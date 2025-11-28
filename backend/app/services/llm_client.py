import json
import re
import requests
import numpy as np


def call_local_llm(
    prompt: str,
    model: str = "gpt-oss:20b",
    temperature: float = 0.1,
    timeout: int = 300,
    max_tokens: int | None = None,
) -> str:
    """调用本地 Ollama 大模型，返回生成的文本。

    默认访问 http://localhost:11434/api/chat
    """
    url = "http://localhost:11434/api/chat"
    options: dict = {"temperature": temperature}
    # 限制最大生成 token 数，避免输出过长导致耗时和解析压力
    if max_tokens is not None and max_tokens > 0:
        options["num_predict"] = int(max_tokens)

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": options,
    }

    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]


def build_forecast_prompt(values, horizon: int, timestamps: list[str] | None = None) -> str:
    """根据历史序列构造时间序列预测 Prompt（直接在原始数值空间）。

    values: 一维数组，按时间从旧到新，数值为真实量纲（例如流量/负荷）。
    timestamps: 与 values 等长的时间索引字符串列表（可选），用于提供额外时间信息。
    """

    series_str = ", ".join(f"{float(v):.4f}" for v in values)

    if timestamps is not None and len(timestamps) == len(values):
        paired_lines = "\n".join(
            f"- {ts}: {float(v):.4f}" for ts, v in zip(timestamps, values)
        )
        history_block = f"最近的历史数据（从旧到新）如下：\n数值序列：\n[{series_str}]\n\n时间戳与数值对应关系：\n{paired_lines}"
    else:
        history_block = f"最近的历史数据（从旧到新）如下：\n[{series_str}]"

    return f"""
你是一名时间序列预测助手，分析的是一个等间隔采样的数值时间序列。

{history_block}

请严格基于以上给出的历史观测数据（以及对应的时间戳），推断接下来 {horizon} 个时间步的数值变化，
而不是编造与历史无关的示例序列。未来的整体水平应与最近一段历史的均值和波动幅度大致相当，
并尽量延续最近一段的日周期/趋势形态，可以有适度起伏，但不要出现长时间完全平坦的常数段，
也不要出现与历史尺度严重不一致的离谱数值。

    如果你无法为所有未来时间步给出完全不同的数值，也必须仍然输出长度为 {horizon}
    的数组；在这种情况下，可以在你最后一个有信心的预测值之后，简单地重复该值，
    直到数组长度达到 {horizon}，而不要缩短数组或输出更少的元素。

    非常重要：下面的格式要求会被程序自动解析，请务必完全遵守，否则会被判定为错误答案。

    严格按照以下格式输出：
    1. 只输出一个 JSON 数组，不要任何多余文字、解释性句子、HTML/脚本标签、代码块标记或示例（不要使用 ```、```json 等标记）。
    2. JSON 数组必须是一维的纯数值数组，形如 [1.23, 4.56, 7.89]。禁止输出任意对象（禁止出现花括号 {{ }}）、禁止包含 x、y、value、date 等键，禁止输出嵌套数组。
    3. 数组长度必须正好为 {horizon}，不能多也不能少。如果你只预测出了前几步，后面的元素必须用你最后一个预测值重复填充，直到长度达到 {horizon}。
    4. 每个元素必须是数字（float），不要字符串，不要在元素中再嵌套任何键值对；只使用半角英文逗号和句点（例如 1.23, 4.56），不要使用全角标点。
    5. 在这个数组的前后都不要再输出任何其他内容（包括注释、解释、自然语言说明等），整个回答必须只包含这一行或多行排版的数组文本。

""".strip()


def parse_forecast_response(text: str, horizon: int):
    """从大模型返回的文本中提取 JSON 数组，并做长度/类型校验。

    为了兼容大模型在数组前后输出的说明文字或额外内容，这里使用
    非贪婪正则只提取第一个形如 "[...]" 的片段进行解析。
    """

    # 非贪婪匹配第一个中括号数组，忽略前后多余文本
    m = re.search(r"\[[\s\S]*?\]", text)

    vals: list[float] = []

    if m:
        # 情况一：存在形如 "[...]" 的片段，优先从中解析
        arr_str = m.group(0)

        # 优先尝试严格 JSON 解析
        try:
            data = json.loads(arr_str)
            if isinstance(data, list):
                # 支持两种常见形式：
                # 1) [1.0, 2.3, ...]
                # 2) [{"value": 1.0}, {"value": 2.3}, ...]
                for x in data:
                    # 对象形式：优先取 "value" 字段或第一个数值字段
                    if isinstance(x, dict):
                        if "value" in x:
                            try:
                                vals.append(float(x["value"]))
                                continue
                            except Exception:
                                pass
                        # 没有 value 键时，寻找第一个数值型字段
                        num_found = False
                        for v in x.values():
                            try:
                                fv = float(v)
                                vals.append(fv)
                                num_found = True
                                break
                            except Exception:
                                continue
                        if num_found:
                            continue
                    # 非对象形式：直接尝试转成 float
                    try:
                        vals.append(float(x))
                    except Exception:
                        continue
            else:
                raise ValueError("LLM 返回的不是数组")
        except Exception:
            # 当数组格式不完全符合 JSON（缺逗号等）时，退化为直接用正则抓取数字序列
            number_pattern = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
            nums = re.findall(number_pattern, arr_str)
            for s in nums:
                try:
                    vals.append(float(s))
                except Exception:
                    continue
    else:
        # 情况二：模型根本没有输出方括号数组，直接在整段文本中抓取数字序列
        number_pattern = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
        nums = re.findall(number_pattern, text)
        for s in nums:
            try:
                vals.append(float(s))
            except Exception:
                continue

    if not vals:
        raise ValueError("LLM 返回数组为空")

    if len(vals) < horizon:
        last = vals[-1]
        vals = vals + [last] * (horizon - len(vals))

    return vals[:horizon]


def run_llm_forecast(series, horizon: int, cfg: dict | None = None) -> list[float]:
    """对单个地区序列使用本地大模型做预测。

    series: pandas.Series / list / np.ndarray，按时间顺序
    horizon: 预测点数
    cfg: 前端传入的 llm_config，可包含: model, temperature, days_window, tokens_per_step
    """

    cfg = cfg or {}

    # 原始数值序列
    values = np.asarray(series, dtype=float)

    # 可选：从 pandas Series 中提取时间索引，以字符串形式传入 Prompt
    timestamps: list[str] | None = None
    try:
        idx = getattr(series, "index", None)
        if idx is not None and len(idx) == len(values):
            timestamps = [str(t) for t in idx]
    except Exception:
        timestamps = None

    # 可选：仅使用最近 days_window 天的数据，和其它模型保持一致的窗口语义
    days_window = int(cfg.get("days_window", 0) or 0)
    base_period = 144  # 10 分钟粒度下的一天步数，与其它模型默认保持一致
    if days_window > 0:
        max_points = days_window * base_period
        if len(values) > max_points:
            values = values[-max_points:]
            if timestamps is not None and len(timestamps) > max_points:
                timestamps = timestamps[-max_points:]

    # 让大模型看到窗口内的全部历史（在 prediction_service 中已经通过 days_window 控制窗口长度）
    tail = values
    tail_ts = timestamps if timestamps is not None and len(timestamps) == len(values) else None

    model = cfg.get("model", "gpt-oss:20b")

    # 略微提高默认温度，使预测不至于过于收缩到均值附近
    temperature = float(cfg.get("temperature", 0.25))
    timeout = int(cfg.get("timeout", 300))

    horizon = int(horizon)

    # 粗略限制 LLM 生成 token 上限：每个预测点分配少量 token 空间
    # 默认 4，可通过 cfg.tokens_per_step 覆盖
    tokens_per_step = int(cfg.get("tokens_per_step", 4) or 4)
    if tokens_per_step <= 0:
        tokens_per_step = 4

    max_tokens = max(32, horizon * tokens_per_step)

    # 使用最近一段原始数值构造 Prompt（如果可用则附带时间戳）
    prompt = build_forecast_prompt(tail, horizon, tail_ts)

    # 不再在控制台打印完整 Prompt 和模型原始输出，避免泄露业务数据、刷屏控制台。
    # 如需调试，可临时打印长度等匿名信息，例如：len(prompt)、len(raw)。

    raw = call_local_llm(
        prompt,
        model=model,
        temperature=temperature,
        timeout=timeout,
        max_tokens=max_tokens,
    )

    # 解析预测值；若失败则退化为简单基线预测，避免整条流水线报错中断。

    try:
        forecast_vals = parse_forecast_response(raw, horizon)
        if not forecast_vals:
            raise ValueError("LLM 解析结果为空")
        forecast_arr = np.asarray(forecast_vals, dtype=float)

    except Exception:
        # 基线策略：直接在原始数值空间使用最近一段的均值作为常数预测.
        mean_val = float(np.mean(tail)) if tail.size > 0 else 0.0
        forecast_arr = np.full(int(horizon), mean_val, dtype=float)

    return forecast_arr.tolist()
<template>
  <el-dropdown @command="handleCommand" placement="bottom-end">
    <el-button type="primary" size="small" class="theme-toggle-btn header-chip" aria-haspopup="true" aria-label="选择主题">
      主题
      <i class="el-icon-arrow-down el-icon--right"></i>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="theme-spring">
          <div class="theme-option"><span class="theme-swatch sw-spring"></span>Spring</div>
        </el-dropdown-item>
        <el-dropdown-item command="theme-summer">
          <div class="theme-option"><span class="theme-swatch sw-summer"></span>Summer</div>
        </el-dropdown-item>
        <el-dropdown-item command="theme-autumn">
          <div class="theme-option"><span class="theme-swatch sw-autumn"></span>Autumn</div>
        </el-dropdown-item>
        <el-dropdown-item command="theme-winter">
          <div class="theme-option"><span class="theme-swatch sw-winter"></span>Winter</div>
        </el-dropdown-item>
        <el-dropdown-item command="theme-aurora">
          <div class="theme-option"><span class="theme-swatch sw-aurora"></span>Aurora</div>
        </el-dropdown-item>
        <el-dropdown-item command="reset">
          <div class="theme-option">恢复默认</div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script>
import { onMounted } from 'vue'

export default {
  name: 'ThemeSelector',
  setup() {
    const themes = ['theme-warm','theme-spring','theme-summer','theme-autumn','theme-winter','theme-aurora']

    const applyTheme = (themeClass) => {
      const root = document.documentElement
      themes.forEach(t => root.classList.remove(t))
      if (themeClass && themes.includes(themeClass)) {
        root.classList.add(themeClass)
        localStorage.setItem('selectedTheme', themeClass)
      }
    }

    const resetTheme = () => {
      const root = document.documentElement
      themes.forEach(t => root.classList.remove(t))
      localStorage.removeItem('selectedTheme')
      localStorage.removeItem('themeWarm')
    }

    const handleCommand = (cmd) => {
      if (cmd === 'reset') {
        resetTheme()
      } else {
        applyTheme(cmd)
      }
    }

    onMounted(() => {
      const sel = localStorage.getItem('selectedTheme')
      if (sel && themes.includes(sel)) {
        document.documentElement.classList.add(sel)
      }
      const warm = localStorage.getItem('themeWarm')
      if (warm === 'true') document.documentElement.classList.add('theme-warm')
    })

    return { handleCommand }
  }
}
</script>

<style scoped>
/* 组件局部样式可复用全局的 .theme-option/.theme-swatch */
</style>

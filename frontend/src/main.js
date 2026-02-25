/**
 * 前端入口文件，整个 Vue 应用从这里启动。
 * 主要做几件事：
 *   1. 引入 Element Plus UI 框架（中文语言包）
 *   2. 全局注册所有 Element Plus 图标
 *   3. 挂载 Pinia 状态管理 和 Vue Router 路由
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

// 把所有 Element Plus 图标注册为全局组件，这样在模板里可以直接 <Edit /> 这样用
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')

<script setup lang="ts">
// 登录页：左侧品牌信息区 + 右侧登录卡片。
// 账号可记住（仅存用户名，不存密码）；开发环境显示种子账号提示。
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { addDynamicRoutes } from '@/router'
import { APP_TITLE } from '@/constants'

const REMEMBER_KEY = 'mes_login_username'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const rememberedName = localStorage.getItem(REMEMBER_KEY) ?? ''
const form = reactive({ username: rememberedName, password: '' })
const remember = ref(Boolean(rememberedName))
const loading = ref(false)
const isDev = computed(() => import.meta.env.DEV)

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid || loading.value) return
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    if (remember.value) localStorage.setItem(REMEMBER_KEY, form.username)
    else localStorage.removeItem(REMEMBER_KEY)
    const home = addDynamicRoutes()
    // redirect 只在指向具体页面时采用；'/' 要靠 Layout 子路由重定向，易在重建时序里落 404，故一律回首页
    const redirect = route.query.redirect as string | undefined
    const target = redirect && redirect !== '/' && redirect !== '/login' ? redirect : home
    await router.replace(target)
  } catch {
    ElMessage.error('登录失败，请检查账号或密码')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <!-- 左：品牌与能力说明（窄屏隐藏） -->
    <aside class="brand">
      <div class="brand-glow" aria-hidden="true" />
      <div class="brand-grid" aria-hidden="true" />

      <header class="brand-head">
        <span class="brand-mark">MES</span>
        <span class="brand-name">{{ APP_TITLE }}</span>
      </header>

      <div class="brand-body">
        <h1>从订单到交付，<br />一屏掌握车间实况</h1>
        <p class="brand-sub">计划、工单、报工、质检、库存与看板串成闭环，现场数据实时回流。</p>

        <ul class="brand-points">
          <li>
            <el-icon><Calendar /></el-icon>
            <div>
              <strong>计划与工单</strong>
              <span>销售订单转生产计划，计划下发为工单并跟踪进度</span>
            </div>
          </li>
          <li>
            <el-icon><Odometer /></el-icon>
            <div>
              <strong>扫码报工与质检</strong>
              <span>移动端扫码报工，来料、过程、最终检验全过程留痕</span>
            </div>
          </li>
          <li>
            <el-icon><DataLine /></el-icon>
            <div>
              <strong>库存与看板</strong>
              <span>出入库流水、齐套分析与产量合格率看板实时可视</span>
            </div>
          </li>
        </ul>
      </div>

      <footer class="brand-foot">© 2026 MES · 生产制造执行系统</footer>
    </aside>

    <!-- 右：登录卡片 -->
    <main class="panel">
      <div class="card">
        <div class="card-head">
          <h2>欢迎登录</h2>
          <p>请使用企业账号登录，未开通请联系系统管理员</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="0"
          size="large"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="请输入账号" clearable autocomplete="username">
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              show-password
              autocomplete="current-password"
            >
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
          </el-form-item>

          <div class="card-row">
            <el-checkbox v-model="remember">记住账号</el-checkbox>
          </div>

          <el-button class="submit" type="primary" size="large" :loading="loading" @click="handleLogin">
            {{ loading ? '登录中…' : '登 录' }}
          </el-button>
        </el-form>

        <p v-if="isDev" class="dev-tip">开发环境种子账号：<code>admin</code> / <code>admin123</code></p>
        <p class="version">内部系统 · v0.1.0</p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

/* ── 左侧品牌区 ─────────────────────────────────────── */
.brand {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  flex: 1 1 52%;
  min-width: 420px;
  padding: 40px 56px;
  color: #e8f1ff;
  background: linear-gradient(155deg, #081524 0%, #0e2440 52%, #13314f 100%);
  overflow: hidden;
}
/* 缓慢呼吸的光斑 + 细网格，纯 CSS，不依赖图片 */
.brand-glow {
  position: absolute;
  top: -18%;
  right: -12%;
  width: 620px;
  height: 620px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(64, 158, 255, 0.34) 0%, rgba(64, 158, 255, 0) 66%);
  animation: breathe 9s ease-in-out infinite;
}
.brand-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.85), transparent 78%);
}
.brand-head,
.brand-body,
.brand-foot {
  position: relative;
  z-index: 1;
}
.brand-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #0a1a2c;
  background: linear-gradient(140deg, #8ec5ff, #4f9bf5);
}
.brand-name {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.brand-body {
  max-width: 480px;
  margin: 24px 0;
}
.brand-body h1 {
  margin: 0 0 16px;
  font-size: 30px;
  line-height: 1.42;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.brand-sub {
  margin: 0 0 34px;
  font-size: 14px;
  line-height: 1.85;
  color: rgba(220, 234, 255, 0.72);
}
.brand-points {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.brand-points li {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.brand-points .el-icon {
  flex: none;
  margin-top: 2px;
  font-size: 18px;
  color: #7cb8ff;
}
.brand-points strong {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}
.brand-points span {
  font-size: 12.5px;
  line-height: 1.7;
  color: rgba(206, 224, 248, 0.62);
}
.brand-foot {
  font-size: 12px;
  color: rgba(180, 205, 235, 0.45);
}

/* ── 右侧登录卡片 ───────────────────────────────────── */
.panel {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 1 48%;
  min-width: 380px;
  padding: 40px 24px;
  background: #f5f7fa;
}
.card {
  width: 100%;
  max-width: 400px;
  padding: 40px 36px 28px;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 18px 48px rgba(15, 42, 74, 0.1), 0 2px 6px rgba(15, 42, 74, 0.06);
  animation: enter 0.45s cubic-bezier(0.22, 0.8, 0.3, 1) both;
}
.card-head {
  margin-bottom: 26px;
}
.card-head h2 {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 600;
  color: #1f2d3d;
}
.card-head p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: #909399;
}
.card-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -4px 0 18px;
}
.submit {
  width: 100%;
  height: 44px;
  font-size: 15px;
  letter-spacing: 2px;
  border-radius: 8px;
}
.dev-tip {
  margin: 18px 0 0;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  text-align: center;
  color: #7a6a3d;
  background: #fdf6e3;
}
.dev-tip code {
  padding: 1px 5px;
  border-radius: 3px;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  color: #8a5a00;
  background: #f7ecd0;
}
.version {
  margin: 16px 0 0;
  font-size: 11.5px;
  text-align: center;
  color: #c0c4cc;
}

/* 输入框在 large 尺寸下再抬高一点，接近主流后台观感 */
.card :deep(.el-input__wrapper) {
  height: 44px;
  border-radius: 8px;
}
.card :deep(.el-form-item) {
  margin-bottom: 20px;
}

@keyframes breathe {
  0%, 100% { opacity: 0.75; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.06); }
}
@keyframes enter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 窄屏：隐藏品牌区，只留卡片 */
@media (max-width: 900px) {
  .brand { display: none; }
  .panel { flex: 1 1 100%; min-width: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .brand-glow, .card { animation: none; }
}
</style>

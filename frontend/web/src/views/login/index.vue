<script setup lang="ts">
// 登录页：左侧品牌信息区 + 右侧登录卡片（含图片验证码）。
// 交互依据「登录图片验证码增量契约」：
//   打开即取图；点图换图并清空输入；到期显示「已过期，点击刷新」；连点防抖且只接受最新响应；
//   2004/2005 清空验证码并换图（保留账号密码）；1001 只标红字段；提示由请求层统一弹，本页不重复弹。
import { computed, onUnmounted, reactive, ref, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { addDynamicRoutes } from '@/router'
import { getCaptcha } from '@/api'
import { ApiError } from '@/api/request'
import { BIZ_CODE, LOCAL_CODE } from '@/constants/biz'
import { APP_TITLE } from '@/constants'

const REMEMBER_KEY = 'mes_login_username'
const CAPTCHA_LENGTH = 4

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const rememberedName = localStorage.getItem(REMEMBER_KEY) ?? ''
const form = reactive({ username: rememberedName, password: '', captchaCode: '' })
const remember = ref(Boolean(rememberedName))
const loading = ref(false)
const isDev = computed(() => import.meta.env.DEV)

// ── 验证码状态 ──────────────────────────────────────────────
const captcha = reactive({
  id: '',
  image: '',
  loading: false,
  /** 取图失败（网络/503） */
  failed: false,
  /** 已到期，需用户点击刷新 */
  expired: false,
  /** 剩余秒数，仅用于提示 */
  remain: 0,
})
let seq = 0
let countdown: number | undefined

function clearCountdown() {
  if (countdown) window.clearInterval(countdown)
  countdown = undefined
}

function scheduleExpire(seconds: number) {
  clearCountdown()
  captcha.remain = seconds
  countdown = window.setInterval(() => {
    captcha.remain -= 1
    if (captcha.remain <= 0) {
      captcha.expired = true
      clearCountdown()
    }
  }, 1000)
}

async function loadCaptcha() {
  if (captcha.loading) return
  const my = ++seq
  captcha.loading = true
  captcha.failed = false
  try {
    const res = await getCaptcha()
    if (my !== seq) return // 已有更新的请求，丢弃本次响应
    captcha.id = res.captchaId
    captcha.image = res.image
    captcha.expired = false
    form.captchaCode = ''
    scheduleExpire(res.expiresIn)
  } catch {
    if (my !== seq) return
    captcha.failed = true
    captcha.id = ''
    captcha.image = ''
    clearCountdown()
  } finally {
    if (my === seq) captcha.loading = false
  }
}

/** 输入即过滤：只留字母数字、转大写、限长 */
function onCaptchaInput(value: string) {
  form.captchaCode = value.replace(/[^0-9a-zA-Z]/g, '').slice(0, CAPTCHA_LENGTH).toUpperCase()
  nextTick(() => formRef.value?.clearValidate('captchaCode'))
}

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captchaCode: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid || loading.value) return

  if (!captcha.id || captcha.expired) {
    ElMessage.warning(
      captcha.failed ? '验证码获取失败，请点击图片重试'
        : captcha.expired ? '验证码已过期，请点击图片刷新'
          : '请先获取验证码',
    )
    loadCaptcha()
    return
  }

  loading.value = true
  try {
    await auth.login({
      username: form.username,
      password: form.password,
      captchaId: captcha.id,
      captchaCode: form.captchaCode,
    })
    if (remember.value) localStorage.setItem(REMEMBER_KEY, form.username)
    else localStorage.removeItem(REMEMBER_KEY)

    const home = addDynamicRoutes()
    // redirect 只在指向具体页面时采用；'/' 要靠 Layout 子路由重定向，易在重建时序里落 404
    const redirect = route.query.redirect as string | undefined
    const target = redirect && redirect !== '/' && redirect !== '/login' ? redirect : home
    clearCountdown()
    await router.replace(target)
  } catch (error) {
    // 提示已由请求层统一弹出，这里只按业务码调整表单
    const code = error instanceof ApiError ? error.code : undefined
    if (code === BIZ_CODE.CAPTCHA_INVALID || code === BIZ_CODE.BAD_CREDENTIALS) {
      // 验证码已被后端消费，必须换图；账号密码保留
      loadCaptcha()
    } else if (code === LOCAL_CODE.TIMEOUT || code === LOCAL_CODE.NETWORK) {
      // 超时/断网：旧 ID 可能已被消费，重试前先换图
      loadCaptcha()
    }
    // 1001 字段校验：保留当前图片，仅由表单规则标红
  } finally {
    loading.value = false
  }
}

// 记住账号被取消时同步清掉本地记录
watch(remember, (on) => {
  if (!on) localStorage.removeItem(REMEMBER_KEY)
})

loadCaptcha()
onUnmounted(clearCountdown)
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

          <el-form-item prop="captchaCode">
            <div class="captcha-row">
              <el-input
                :model-value="form.captchaCode"
                placeholder="请输入验证码"
                maxlength="4"
                autocomplete="off"
                spellcheck="false"
                @input="onCaptchaInput"
              >
                <template #prefix><el-icon><Key /></el-icon></template>
              </el-input>

              <button
                type="button"
                class="captcha-img"
                :class="{ 'is-done': captcha.loading }"
                :disabled="captcha.loading"
                title="点击换一张"
                @click="loadCaptcha"
              >
                <img v-if="captcha.image && !captcha.expired" :src="captcha.image" alt="验证码" />
                <span v-if="captcha.loading" class="captcha-tip">加载中…</span>
                <span v-else-if="captcha.failed" class="captcha-tip">点击重试</span>
                <span v-else-if="captcha.expired" class="captcha-tip">点击刷新</span>
                <span v-else-if="!captcha.image" class="captcha-tip">点击获取</span>
              </button>
            </div>
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

/* 验证码一行：输入框 + 图片 */
.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.captcha-row .el-input {
  flex: 1;
}
.captcha-img {
  position: relative;
  flex: none;
  width: 116px;
  height: 44px;
  padding: 0;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #f5f7fa;
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.15s;
}
.captcha-img:hover:not(:disabled) {
  border-color: #409eff;
}
.captcha-img:disabled {
  cursor: progress;
}
.captcha-img img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.captcha-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 13px;
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

@media (max-width: 900px) {
  .brand { display: none; }
  .panel { flex: 1 1 100%; min-width: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .brand-glow, .card { animation: none; }
}
</style>

<script setup lang="ts">
// 登录页：浅蓝科技风左右分栏布局。
// 保留原有登录、验证码、记住账号及动态路由逻辑。
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

// 验证码状态
const captcha = reactive({
  id: '',
  image: '',
  loading: false,
  failed: false,
  expired: false,
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
    if (my !== seq) return
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
    const redirect = route.query.redirect as string | undefined
    const target = redirect && redirect !== '/' && redirect !== '/login' ? redirect : home
    clearCountdown()
    await router.replace(target)
  } catch (error) {
    const code = error instanceof ApiError ? error.code : undefined
    if (code === BIZ_CODE.CAPTCHA_INVALID || code === BIZ_CODE.BAD_CREDENTIALS) {
      loadCaptcha()
    } else if (code === LOCAL_CODE.TIMEOUT || code === LOCAL_CODE.NETWORK) {
      loadCaptcha()
    }
  } finally {
    loading.value = false
  }
}

watch(remember, (on) => {
  if (!on) localStorage.removeItem(REMEMBER_KEY)
})

loadCaptcha()
onUnmounted(clearCountdown)
</script>

<template>
  <main class="login-page">
    <div class="ambient ambient-one" aria-hidden="true"></div>
    <div class="ambient ambient-two" aria-hidden="true"></div>

    <div class="login-layout">
      <!-- 左侧品牌展示区 -->
      <section class="intro-panel">
        <header class="brand">
          <span class="brand-mark">MES</span>
          <div class="brand-text">
            <strong>{{ APP_TITLE }}</strong>
            <span>Production Execution System</span>
          </div>
        </header>

        <div class="intro-copy">
          <div class="eyebrow">
            <span class="eyebrow-dot"></span>
            SMART MANUFACTURING PLATFORM
          </div>
          <h1>智能制造 <span>·</span> 高效生产</h1>
          <p>连接生产现场 · 透明管理流程 · 提升制造效能</p>
        </div>

        <!-- 纯 SVG 插画，不依赖图片资源 -->
        <div class="factory-visual" aria-hidden="true">
          <div class="visual-glow"></div>
          <svg class="factory-svg" viewBox="0 0 620 390" role="img">
            <defs>
              <linearGradient id="chipTop" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#72B8FF"/>
                <stop offset="100%" stop-color="#2467E8"/>
              </linearGradient>
              <linearGradient id="chipSide" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#5EA7FF"/>
                <stop offset="100%" stop-color="#2D6DE0"/>
              </linearGradient>
              <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#FFFFFF" stop-opacity=".9"/>
                <stop offset="100%" stop-color="#BBD9FF" stop-opacity=".48"/>
              </linearGradient>
              <filter id="softShadow" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="12"/>
              </filter>
            </defs>

            <ellipse cx="310" cy="320" rx="235" ry="35" fill="#5C9FF4" opacity=".16" filter="url(#softShadow)"/>
            <ellipse cx="310" cy="292" rx="250" ry="76" fill="none" stroke="#FFFFFF" stroke-opacity=".72" stroke-width="1.5"/>
            <ellipse cx="310" cy="292" rx="208" ry="58" fill="none" stroke="#A8CEFF" stroke-opacity=".55" stroke-width="1.2"/>

            <!-- 悬浮信息面板 -->
            <g transform="translate(100 112)">
              <path d="M0 28 L78 0 Q86 -3 86 7 L86 95 Q86 103 78 106 L0 134 Q-8 137 -8 127 L-8 39 Q-8 31 0 28Z"
                    fill="url(#glass)" stroke="#8DBEFF" stroke-width="1.5"/>
              <g fill="#5B9BEA" opacity=".82">
                <rect x="13" y="73" width="9" height="25" rx="2"/>
                <rect x="29" y="59" width="9" height="39" rx="2"/>
                <rect x="45" y="44" width="9" height="54" rx="2"/>
                <rect x="61" y="32" width="9" height="66" rx="2"/>
              </g>
              <path d="M10 108 L72 86" stroke="#FFFFFF" stroke-width="2" opacity=".8"/>
            </g>

            <g transform="translate(425 116)">
              <path d="M0 20 L68 0 Q76 -2 76 7 L76 91 Q76 99 68 102 L0 122 Q-8 124 -8 115 L-8 29 Q-8 22 0 20Z"
                    fill="url(#glass)" stroke="#8DBEFF" stroke-width="1.5"/>
              <g transform="translate(34 61)" fill="none" stroke="#4F91E8" stroke-width="7" stroke-linecap="round">
                <circle r="22" stroke-dasharray="8 7"/>
                <circle r="8" fill="#4F91E8" stroke="none"/>
              </g>
            </g>

            <g transform="translate(265 40)">
              <path d="M0 18 L70 0 Q78 -2 78 7 L78 88 Q78 96 70 99 L0 117 Q-8 119 -8 110 L-8 27 Q-8 20 0 18Z"
                    fill="url(#glass)" stroke="#8DBEFF" stroke-width="1.5"/>
              <g fill="#5B9BEA">
                <rect x="15" y="61" width="9" height="28" rx="2"/>
                <rect x="31" y="45" width="9" height="44" rx="2"/>
                <rect x="47" y="29" width="9" height="60" rx="2"/>
              </g>
            </g>

            <!-- 分层底座 -->
            <path d="M128 276 L298 215 Q310 211 323 216 L490 276 L321 342 Q310 346 298 342Z"
                  fill="#A9CEFF" opacity=".28"/>
            <path d="M150 263 L300 211 Q310 207 321 211 L470 263 L320 320 Q310 324 300 320Z"
                  fill="#FFFFFF" fill-opacity=".62" stroke="#A9CFFF" stroke-width="1.5"/>
            <path d="M150 263 L300 315 Q310 319 320 315 L470 263 L470 278 L320 335 Q310 339 300 335 L150 278Z"
                  fill="#C7E0FF" opacity=".85"/>
            <path d="M183 238 L300 198 Q310 194 320 198 L437 238 L320 282 Q310 286 300 282Z"
                  fill="#D9EBFF" stroke="#A9CCF8" stroke-width="1.5"/>
            <path d="M183 238 L300 278 Q310 282 320 278 L437 238 L437 252 L320 296 Q310 300 300 296 L183 252Z"
                  fill="#A8CCFA" opacity=".8"/>

            <!-- MES 主芯片 -->
            <path d="M218 204 L302 173 Q310 170 318 173 L402 204 L318 237 Q310 240 302 237Z"
                  fill="url(#chipTop)" stroke="#78B6FF" stroke-width="1.5"/>
            <path d="M218 204 L302 235 Q310 238 318 235 L402 204 L402 221 L318 254 Q310 257 302 254 L218 221Z"
                  fill="url(#chipSide)"/>
            <path d="M218 204 L302 235 Q310 238 318 235 L402 204" fill="none" stroke="#BFE0FF" stroke-width="1.5"/>
            <text x="310" y="216" fill="#FFFFFF" font-size="23" font-weight="800" text-anchor="middle"
                  letter-spacing="2" transform="rotate(17 310 216)">MES</text>

            <!-- 芯片连接线 -->
            <g stroke="#FFFFFF" stroke-width="2" opacity=".7">
              <path d="M310 254 V276"/>
              <path d="M250 232 L220 248"/>
              <path d="M370 232 L400 248"/>
            </g>
            <g fill="#FFFFFF" opacity=".9">
              <circle cx="310" cy="276" r="3"/>
              <circle cx="220" cy="248" r="3"/>
              <circle cx="400" cy="248" r="3"/>
            </g>
          </svg>
        </div>

        <div class="feature-row">
          <div class="feature-item">
            <span class="feature-icon">01</span>
            <div><strong>生产可视化</strong><small>实时掌握生产动态</small></div>
          </div>
          <span class="feature-divider"></span>
          <div class="feature-item">
            <span class="feature-icon">02</span>
            <div><strong>流程数字化</strong><small>规范制造业务流程</small></div>
          </div>
        </div>
      </section>

      <!-- 右侧登录区 -->
      <section class="form-panel">
        <div class="login-card">
          <header class="card-brand">
            <span class="brand-mark small">MES</span>
            <div class="brand-text">
              <strong>{{ APP_TITLE }}</strong>
              <span>Production Execution System</span>
            </div>
          </header>

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
              <span v-if="!loading" class="submit-arrow">→</span>
            </el-button>
          </el-form>

          <p v-if="isDev" class="dev-tip">
            <span class="dev-tip-label">开发环境种子账号</span>
            <code>admin</code>
            <span class="slash">/</span>
            <code>admin123</code>
          </p>
        </div>
      </section>

      <footer class="page-footer">© 2026 MES · 生产制造执行系统 · v0.1.0</footer>
    </div>
  </main>
</template>

<style scoped>
.login-page {
  --blue: #2878ed;
  --blue-deep: #2459d7;
  --ink: #183b69;
  --muted: #7185a2;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 56px 5vw 40px;
  /* 只裁横向：矮屏（如 1440x800）时允许纵向滚动，否则底部版权与插画会被切掉 */
  overflow-x: hidden;
  isolation: isolate;
  background:
    radial-gradient(ellipse at 16% 15%, rgba(255, 255, 255, .96) 0, rgba(255, 255, 255, .35) 34%, transparent 58%),
    radial-gradient(ellipse at 83% 18%, rgba(183, 213, 255, .58) 0, transparent 43%),
    linear-gradient(125deg, #edf5ff 0%, #e4efff 48%, #dceaff 100%);
}

.login-page::before,
.login-page::after {
  position: absolute;
  z-index: -1;
  right: -8%;
  bottom: -190px;
  left: -8%;
  height: 360px;
  content: "";
  pointer-events: none;
  border: 1px solid rgba(255, 255, 255, .7);
  border-radius: 50% 50% 0 0 / 30% 30% 0 0;
  transform: rotate(-3deg);
}

.login-page::before {
  bottom: -218px;
  background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(109,171,255,.22));
  box-shadow: 0 -12px 36px rgba(255,255,255,.35);
}

.login-page::after {
  bottom: -252px;
  left: 36%;
  height: 300px;
  border-color: rgba(255,255,255,.55);
  background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(91,157,246,.15));
  transform: rotate(5deg);
}

.ambient {
  position: absolute;
  z-index: -1;
  pointer-events: none;
  border-radius: 50%;
  filter: blur(2px);
}

.ambient-one {
  top: -280px;
  right: -120px;
  width: 680px;
  height: 680px;
  border: 1px solid rgba(255,255,255,.42);
  box-shadow: 0 0 0 38px rgba(255,255,255,.08), 0 0 0 78px rgba(255,255,255,.05);
}

.ambient-two {
  bottom: -390px;
  left: -220px;
  width: 780px;
  height: 580px;
  background: radial-gradient(ellipse, rgba(89,159,255,.14), transparent 68%);
}

.login-layout {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(430px, .92fr);
  align-items: center;
  gap: clamp(48px, 7vw, 112px);
  width: min(1240px, 100%);
  margin: auto;
  padding-bottom: 28px;
}

.intro-panel {
  min-width: 0;
  padding: 8px 0 0;
  animation: rise-in .65s cubic-bezier(.2,.75,.25,1) both;
}

.brand,
.card-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand {
  margin-bottom: 52px;
}

.brand-mark {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  color: #fff;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: .4px;
  border-radius: 14px;
  background: linear-gradient(145deg, #3194ff 0%, #1760dc 100%);
  box-shadow: 0 8px 18px rgba(39, 112, 226, .22), inset 0 1px 0 rgba(255,255,255,.35);
}

.brand-mark.small {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  font-size: 14px;
}

.brand-text {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.brand-text strong {
  color: #18385f;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: .2px;
}

.brand-text span {
  color: #8293aa;
  font-size: 13px;
  letter-spacing: .25px;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 16px;
  color: #6b8bb6;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 2px;
}

.eyebrow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #4a96f6;
  box-shadow: 0 0 0 4px rgba(74,150,246,.12);
}

.intro-copy h1 {
  margin: 0;
  color: #1c477e;
  font-size: clamp(34px, 3.2vw, 48px);
  font-weight: 800;
  letter-spacing: 1px;
  line-height: 1.25;
}

.intro-copy h1 span {
  color: #4289eb;
  padding: 0 3px;
}

.intro-copy p {
  margin: 20px 0 0;
  color: #7188a8;
  font-size: 16px;
  letter-spacing: .4px;
  line-height: 1.8;
}

.factory-visual {
  position: relative;
  width: min(100%, 590px);
  margin: 14px auto 0;
}

.visual-glow {
  position: absolute;
  right: 14%;
  bottom: 5%;
  left: 14%;
  height: 28%;
  border-radius: 50%;
  background: rgba(82, 151, 244, .22);
  filter: blur(38px);
}

.factory-svg {
  position: relative;
  display: block;
  width: 100%;
  overflow: visible;
  filter: drop-shadow(0 16px 20px rgba(70, 129, 211, .08));
}

.feature-row {
  display: flex;
  align-items: center;
  gap: 24px;
  margin: -4px 0 0 20px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 11px;
}

.feature-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  color: #347fe1;
  font-size: 10px;
  font-weight: 800;
  border: 1px solid rgba(104, 162, 235, .3);
  border-radius: 10px;
  background: rgba(255,255,255,.52);
}

.feature-item div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.feature-item strong {
  color: #42658f;
  font-size: 12px;
  font-weight: 650;
}

.feature-item small {
  color: #8da0b9;
  font-size: 10px;
}

.feature-divider {
  width: 1px;
  height: 28px;
  background: rgba(104, 145, 195, .24);
}

.form-panel {
  display: flex;
  justify-content: flex-end;
  min-width: 0;
  animation: rise-in .7s .08s cubic-bezier(.2,.75,.25,1) both;
}

.login-card {
  width: 100%;
  max-width: 500px;
  padding: 38px 42px 34px;
  border: 1px solid rgba(255,255,255,.88);
  border-radius: 22px;
  background: rgba(255,255,255,.91);
  box-shadow:
    0 24px 70px rgba(52, 105, 176, .13),
    0 4px 14px rgba(69, 119, 185, .06),
    inset 0 1px 0 rgba(255,255,255,.95);
  backdrop-filter: blur(14px);
}

.card-brand {
  padding-bottom: 22px;
  margin-bottom: 24px;
  border-bottom: 1px solid #edf2f8;
}

.card-brand .brand-text strong {
  font-size: 16px;
}

.card-brand .brand-text span {
  font-size: 12px;
}

.card-head {
  margin-bottom: 25px;
}

.card-head h2 {
  margin: 0 0 8px;
  color: #1d3554;
  font-size: 25px;
  font-weight: 750;
  letter-spacing: .4px;
}

.card-head p {
  margin: 0;
  color: #8a98aa;
  font-size: 13px;
  line-height: 1.7;
}

.login-card :deep(.el-form-item) {
  margin-bottom: 19px;
}

.login-card :deep(.el-input__wrapper) {
  min-height: 48px;
  padding: 1px 14px;
  border: 1px solid #e1e8f1;
  border-radius: 10px;
  background: #fbfdff;
  box-shadow: 0 1px 2px rgba(22, 52, 91, .025);
  transition: border-color .2s ease, box-shadow .2s ease, background .2s ease;
}

.login-card :deep(.el-input__wrapper:hover) {
  border-color: #b8d2f5;
}

.login-card :deep(.el-input__wrapper.is-focus) {
  border-color: #6ca8f4;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, .10);
}

.login-card :deep(.el-input__inner) {
  color: #263b55;
  font-size: 14px;
}

.login-card :deep(.el-input__inner::placeholder) {
  color: #aab5c3;
}

.login-card :deep(.el-input__prefix-inner) {
  color: #9aaabd;
  font-size: 16px;
}

.captcha-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.captcha-row .el-input {
  flex: 1;
  min-width: 0;
}

.captcha-row :deep(.el-input__inner) {
  text-align: left;
  letter-spacing: 2px;
}

.captcha-img {
  position: relative;
  flex: none;
  width: 142px;
  height: 48px;
  padding: 0;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid #e1e8f1;
  border-radius: 10px;
  background: #f3f7fc;
  transition: border-color .2s ease, background .2s ease;
}

.captcha-img:hover:not(:disabled) {
  border-color: #8ab8f3;
  background: #edf5ff;
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
  color: #7188a8;
  font-size: 12px;
}

.card-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 2px 0 22px;
}

.login-card :deep(.el-checkbox__label) {
  color: #5e7695;
  font-size: 13px;
}

.login-card :deep(.el-checkbox__inner) {
  border-color: #b9cbe0;
  border-radius: 4px;
}

.login-card :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  border-color: #3488f2;
  background: #3488f2;
}

.submit {
  width: 100%;
  height: 50px;
  gap: 9px;
  color: #fff;
  font-size: 16px;
  font-weight: 650;
  letter-spacing: 3px;
  border: 0;
  border-radius: 10px;
  background: linear-gradient(105deg, #3299f8 0%, #2878ec 55%, #315be0 100%);
  box-shadow: 0 8px 18px rgba(47, 119, 226, .2);
  transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
}

.submit:hover {
  color: #fff;
  filter: brightness(1.04);
  box-shadow: 0 11px 22px rgba(47, 119, 226, .27);
  transform: translateY(-1px);
}

.submit:active {
  transform: translateY(0);
}

.submit-arrow {
  font-size: 20px;
  font-weight: 400;
  letter-spacing: 0;
}

.dev-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
  margin: 20px 0 0;
  padding: 11px 12px;
  color: #9a793e;
  font-size: 12px;
  border: 1px solid rgba(239, 208, 143, .25);
  border-radius: 9px;
  background: #fff8e9;
}

.dev-tip-label {
  margin-right: 2px;
}

.dev-tip code {
  padding: 2px 6px;
  color: #98651b;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 11px;
  border-radius: 4px;
  background: #f8edcf;
}

.slash {
  color: #c5a66b;
}

.page-footer {
  grid-column: 1 / -1;
  margin: 2px 0 0;
  color: #8298b4;
  font-size: 12px;
  text-align: center;
  letter-spacing: .2px;
}

@keyframes rise-in {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1050px) {
  .login-page {
    padding-right: 4vw;
    padding-left: 4vw;
  }

  .login-layout {
    grid-template-columns: minmax(0, 1fr) minmax(390px, .95fr);
    gap: 38px;
  }

  .login-card {
    padding: 34px 32px 30px;
  }

  .intro-copy h1 {
    font-size: clamp(30px, 3.5vw, 40px);
  }

  .feature-row {
    gap: 14px;
    margin-left: 8px;
  }
}

@media (max-width: 800px) {
  .login-page {
    align-items: flex-start;
    padding: 36px 22px 64px;
    overflow-y: auto;
  }

  .login-layout {
    display: flex;
    width: min(520px, 100%);
    flex-direction: column;
    gap: 24px;
    padding-bottom: 36px;
  }

  .intro-panel {
    width: 100%;
    padding: 0;
  }

  .brand {
    margin-bottom: 28px;
  }

  .brand-mark {
    width: 46px;
    height: 46px;
    border-radius: 12px;
    font-size: 14px;
  }

  .brand-text strong {
    font-size: 16px;
  }

  .intro-copy h1 {
    font-size: clamp(28px, 6vw, 38px);
  }

  .intro-copy p {
    margin-top: 10px;
    font-size: 13px;
  }

  .eyebrow {
    margin-bottom: 10px;
    font-size: 9px;
  }

  .factory-visual {
    display: none;
  }

  .feature-row {
    display: none;
  }

  .form-panel {
    width: 100%;
    justify-content: center;
  }

  .login-card {
    max-width: none;
    padding: 30px 28px 26px;
    border-radius: 18px;
  }

  .page-footer {
    margin-top: 0;
  }
}

@media (max-width: 480px) {
  .login-page {
    padding: 26px 16px 58px;
  }

  .login-layout {
    gap: 20px;
  }

  .brand {
    margin-bottom: 24px;
  }

  .intro-copy h1 {
    font-size: 29px;
  }

  .intro-copy p {
    font-size: 12px;
  }

  .login-card {
    padding: 25px 20px 22px;
  }

  .card-brand {
    padding-bottom: 18px;
    margin-bottom: 21px;
  }

  .card-head h2 {
    font-size: 22px;
  }

  .card-head p {
    font-size: 12px;
  }

  .captcha-row {
    gap: 8px;
  }

  .captcha-img {
    width: 112px;
  }

  .dev-tip {
    font-size: 11px;
  }

  .page-footer {
    font-size: 10px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .intro-panel,
  .form-panel {
    animation: none;
  }

  .submit,
  .captcha-img,
  .login-card :deep(.el-input__wrapper) {
    transition: none;
  }
}
</style>

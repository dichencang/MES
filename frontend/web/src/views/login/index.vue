<script setup lang="ts">
// 登录页：整页深色底 + 居中卡片（品牌信息收进卡片内，避免左右大面积色块对撞）。
// 交互依据「登录图片验证码增量契约」：
//   打开即取图；点图换图并清空输入；到期显示「点击刷新」；连点防抖且只接受最新响应；
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
      loadCaptcha()
    } else if (code === LOCAL_CODE.TIMEOUT || code === LOCAL_CODE.NETWORK) {
      // 超时/断网：旧 ID 可能已被消费，重试前先换图
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
  <div class="login-page">
    <div class="center">
      <section class="card">
        <header class="brand">
          <span class="brand-mark">MES</span>
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
          </el-button>
        </el-form>

        <p v-if="isDev" class="dev-tip">开发环境种子账号：<code>admin</code> / <code>admin123</code></p>
      </section>

      <footer class="foot">© 2026 MES · 生产制造执行系统 · v0.1.0</footer>
    </div>
  </div>
</template>

<style scoped>
/* 整页统一深色底：没有左右分栏，也就没有色块对撞与单侧空旷 */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  background: #f2f4f8;
  /* 有背景图时：把上一行换成下面这行，图放到 web/src/assets/login-bg.jpg 即可（遮罩保证文字与卡片可读）
     background: linear-gradient(rgba(10, 21, 32, 0.45), rgba(10, 21, 32, 0.65)), url('@/assets/login-bg.jpg') center/cover no-repeat; */
}
.center {
  width: 100%;
  max-width: 420px;
}

/* ── 卡片 ─────────────────────────────────────────────── */
.card {
  padding: 32px 36px 28px;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 42, 74, 0.1), 0 2px 6px rgba(15, 42, 74, 0.06);
  animation: enter 0.4s cubic-bezier(0.22, 0.8, 0.3, 1) both;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 20px;
  margin-bottom: 22px;
  border-bottom: 1px solid #edf0f4;
}
.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #ffffff;
  background: linear-gradient(140deg, #3d7fe0, #2461c4);
}
.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.brand-text strong {
  font-size: 14.5px;
  font-weight: 600;
  color: #1f2d3d;
}
.brand-text span {
  font-size: 11px;
  letter-spacing: 0.4px;
  color: #a3a9b3;
}
.card-head {
  margin-bottom: 22px;
}
.card-head h2 {
  margin: 0 0 6px;
  font-size: 21px;
  font-weight: 600;
  color: #1f2d3d;
}
.card-head p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: #909399;
}

/* ── 验证码行 ─────────────────────────────────────────── */
.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.captcha-row .el-input {
  flex: 1;
  min-width: 0;
}
/* 4 位验证码居中 + 字距，宽框里不显空 */
.captcha-row :deep(.el-input__inner) {
  text-align: center;
  letter-spacing: 3px;
}
.captcha-img {
  position: relative;
  flex: none;
  width: 144px;
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
  margin: 2px 0 16px;
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
.foot {
  margin: 18px 0 0;
  font-size: 12px;
  text-align: center;
  color: #a8b0bd;
}

.card :deep(.el-input__wrapper) {
  height: 44px;
  border-radius: 8px;
}
.card :deep(.el-form-item) {
  margin-bottom: 20px;
}

@keyframes enter {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 480px) {
  .card { padding: 26px 20px 22px; }
  .captcha-img { width: 118px; }
}

@media (prefers-reduced-motion: reduce) {
  .card { animation: none; }
}
</style>

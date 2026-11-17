<template>
  <div class="err-page">
    <h1>403</h1>
    <p>没有访问权限，或当前页面未被授权</p>
    <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
  </div>
</template>

<style scoped>
.err-page { height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; }
.err-page h1 { font-size: 72px; margin: 0; color: #e6a23c; }
.err-page p { color: #666; }
</style>

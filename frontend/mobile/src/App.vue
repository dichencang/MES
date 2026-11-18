<script setup lang="ts">
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
onLaunch(() => {
  console.log("MES App Launch");
});
onShow(() => {
  console.log("MES App Show");
});
onHide(() => {
  console.log("MES App Hide");
});
</script>
<style>
/* 全局样式：与 PC Web 主色 #409EFF 对齐的页面底色 */
page {
  background-color: #f5f7fa;
  color: #303133;
  font-size: 14px;
}
</style>

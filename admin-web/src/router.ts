import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './views/HomePage.vue'
import LoginPage from './views/LoginPage.vue'
import MetricsPage from './views/MetricsPage.vue'
import MetricDetailPage from './views/MetricDetailPage.vue'
import AliasesPage from './views/AliasesPage.vue'
import IssuesPage from './views/IssuesPage.vue'
import TasksPage from './views/TasksPage.vue'
import { token } from './auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginPage }, { path: '/', component: HomePage },
    { path: '/standard-metrics', component: MetricsPage },
    { path: '/standard-metrics/:id', component: MetricDetailPage },
    { path: '/metric-aliases', component: AliasesPage },
    { path: '/ocr-metric-issues', component: IssuesPage },
    { path: '/ocr-tasks', component: TasksPage },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
router.beforeEach(to => to.path !== '/login' && !token.value ? '/login' : true)
export default router

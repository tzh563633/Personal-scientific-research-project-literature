import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Setup from './views/Setup.vue'
import Layout from './views/Layout.vue'
import Dashboard from './views/Dashboard.vue'
import Papers from './views/Papers.vue'
import Journals from './views/Journals.vue'
import Code from './views/Code.vue'
import Commands from './views/Commands.vue'
import Reviews from './views/Reviews.vue'
import System from './views/System.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login },
    { path: '/setup', component: Setup },
    {
      path: '/',
      component: Layout,
      children: [
        { path: '', component: Dashboard },
        { path: 'journal-tracking', component: Journals },
        { path: 'folder-analysis', component: Papers },
        { path: 'review-writing', component: Reviews },
        { path: 'research-assets', component: Code },
        { path: 'papers', redirect: '/folder-analysis' },
        { path: 'journals', redirect: '/journal-tracking' },
        { path: 'code', redirect: '/research-assets' },
        { path: 'commands', component: Commands },
        { path: 'reviews', redirect: '/review-writing' },
        { path: 'system', component: System },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.path === '/setup' || to.path === '/login') return true
  if (!localStorage.getItem('token')) return '/login'
  return true
})

export default router

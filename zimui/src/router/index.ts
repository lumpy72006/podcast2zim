import { createRouter, createWebHashHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import EpisodeView from '../views/EpisodeView.vue'
import NotFoundView from '../views/NotFoundView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    // target of the ZIM search entry for the podcast itself (index/podcast)
    { path: '/podcast', redirect: { name: 'home' } },
    // target of the ZIM search entries for episodes (index/<id>)
    {
      path: '/episode/:id',
      name: 'episode',
      component: EpisodeView
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView }
  ],
  scrollBehavior() {
    return { top: 0, behavior: 'smooth' }
  }
})

export default router

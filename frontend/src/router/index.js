/**
 * Vue Router configuration
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/documents/load',
    name: 'DocumentLoad',
    component: () => import('../views/DocumentLoad.vue')
  },
  {
    path: '/documents/chunk',
    name: 'DocumentChunk',
    component: () => import('../views/DocumentChunk.vue')
  },
  {
    path: '/documents/embed',
    name: 'DocumentEmbedding',
    component: () => import('../views/DocumentEmbedding.vue')
  },
  {
    path: '/index',
    name: 'VectorIndex',
    component: () => import('../views/VectorIndex.vue')
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('../views/Search.vue')
  },
  {
    path: '/generation',
    name: 'Generation',
    component: () => import('../views/Generation.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

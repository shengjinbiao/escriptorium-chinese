import Vue from 'vue';
import VueRouter from 'vue-router';
import store from './store';
import App from './App.vue';
import { routes } from './router';

Vue.use(VueRouter);

const router = new VueRouter({
    mode: 'history',
    base: '/gazetteer/',
    routes
});

new Vue({
    el: '#gazetteer-app',
    store,
    router,
    render: h => h(App)
});
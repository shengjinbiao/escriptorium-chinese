import Vue from 'vue';
import VueRouter from 'vue-router';
import GazetteerList from './views/GazetteerList.vue';
import GazetteerDetail from './views/GazetteerDetail.vue';
import EntityList from './views/EntityList.vue';
import EntityDetail from './views/EntityDetail.vue';
import KnowledgeGraph from './views/KnowledgeGraph.vue';

Vue.use(VueRouter);

export const routes = [
    {
        path: '/',
        name: 'gazetteer-list',
        component: GazetteerList,
        meta: { title: '方志列表' }
    },
    {
        path: '/gazetteer/:id',
        name: 'gazetteer-detail',
        component: GazetteerDetail,
        props: true,
        meta: { title: '方志详情' }
    },
    {
        path: '/entities',
        name: 'entity-list',
        component: EntityList,
        meta: { title: '知识实体' }
    },
    {
        path: '/entity/:id',
        name: 'entity-detail',
        component: EntityDetail,
        props: true,
        meta: { title: '实体详情' }
    },
    {
        path: '/graph',
        name: 'knowledge-graph',
        component: KnowledgeGraph,
        meta: { title: '知识图谱' }
    }
];
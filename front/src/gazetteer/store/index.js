import Vue from 'vue';
import Vuex from 'vuex';

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    gazetteers: [],
    entities: [],
    relations: [],
    loading: false,
    error: null
  },
  mutations: {
    SET_GAZETTEERS(state, gazetteers) {
      state.gazetteers = gazetteers;
    },
    SET_ENTITIES(state, entities) {
      state.entities = entities;
    },
    SET_RELATIONS(state, relations) {
      state.relations = relations;
    },
    SET_LOADING(state, loading) {
      state.loading = loading;
    },
    SET_ERROR(state, error) {
      state.error = error;
    }
  },
  actions: {
    async fetchGazetteers({ commit }) {
      try {
        commit('SET_LOADING', true);
        const response = await fetch('/api/gazetteer/');
        const data = await response.json();
        commit('SET_GAZETTEERS', data);
      } catch (error) {
        commit('SET_ERROR', error.message);
      } finally {
        commit('SET_LOADING', false);
      }
    },
    async fetchEntities({ commit }) {
      try {
        commit('SET_LOADING', true);
        const response = await fetch('/api/gazetteer/entities/');
        const data = await response.json();
        commit('SET_ENTITIES', data);
      } catch (error) {
        commit('SET_ERROR', error.message);
      } finally {
        commit('SET_LOADING', false);
      }
    }
  },
  getters: {
    allGazetteers: state => state.gazetteers,
    allEntities: state => state.entities,
    allRelations: state => state.relations,
    isLoading: state => state.loading,
    error: state => state.error
  }
});
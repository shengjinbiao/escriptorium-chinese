<template>
    <EscrModal v-if="visible">
        <template #modal-header>
            <div class="knowledge-tree__header">
                <h3>Knowledge Tree</h3>
                <p class="knowledge-tree__subtitle">
                    {{ summaryLine }}
                </p>
            </div>
        </template>
        <template #modal-content="{ scroll }">
            <div class="knowledge-tree__content">
                <section class="knowledge-tree__section">
                    <h4>Overview</h4>
                    <ul class="knowledge-tree__stats">
                        <li>
                            <strong>Project:</strong>
                            <span>{{ projectName }}</span>
                        </li>
                        <li v-if="hasDocument">
                            <strong>Document:</strong>
                            <span>{{ data.document.name }}</span>
                        </li>
                        <li>
                            <strong>Passages:</strong>
                            <span>{{ passageCount }}</span>
                        </li>
                        <li>
                            <strong>Clusters:</strong>
                            <span>{{ clusterCount }}</span>
                        </li>
                        <li v-if="parts.length">
                            <strong>Selected Images:</strong>
                            <span>{{ parts.length }}</span>
                        </li>
                    </ul>
                </section>

                <section class="knowledge-tree__section" v-if="documents.length">
                    <h4>Documents</h4>
                    <ul class="knowledge-tree__list">
                        <li v-for="doc in documents" :key="doc.id">
                            <div class="knowledge-tree__doc">
                                <span class="knowledge-tree__doc-name">{{ doc.name }}</span>
                                <span class="knowledge-tree__badge">{{ doc.passages }} passages</span>
                            </div>
                        </li>
                    </ul>
                </section>

                <section
                    class="knowledge-tree__section knowledge-tree__layout"
                    v-if="treeData.length"
                >
                    <div class="knowledge-tree__tree">
                        <h4>Knowledge Tree</h4>
                        <ul class="knowledge-tree__tree-root">
                            <li
                                v-for="cluster in treeData"
                                :key="cluster.id"
                            >
                                <button
                                    type="button"
                                    class="knowledge-tree__tree-node"
                                    :class="{ 'is-active': isSelectedCluster(cluster) }"
                                    @click="selectCluster(cluster)"
                                >
                                    <span class="knowledge-tree__tree-label">
                                        {{ cluster.label }}
                                    </span>
                                    <span class="knowledge-tree__badge">
                                        {{ cluster.passages.length }}
                                    </span>
                                </button>
                                <ul
                                    v-if="cluster.passages.length"
                                    class="knowledge-tree__tree-children"
                                >
                                    <li
                                        v-for="passage in cluster.passages"
                                        :key="passage.id"
                                    >
                                        <button
                                            type="button"
                                            class="knowledge-tree__tree-node knowledge-tree__tree-node--child"
                                            :class="{ 'is-active': isSelectedPassage(cluster, passage) }"
                                            @click="selectPassage(cluster, passage)"
                                        >
                                            <span class="knowledge-tree__tree-label">
                                                {{ passage.label }}
                                            </span>
                                        </button>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                    <div class="knowledge-tree__detail" v-if="selectedNode">
                        <h4>{{ selectedNodeTitle }}</h4>
                        <p class="knowledge-tree__detail-meta" v-if="selectedNodeMeta">
                            {{ selectedNodeMeta }}
                        </p>
                        <p
                            v-if="selectedNodeSummary"
                            class="knowledge-tree__detail-summary"
                        >
                            {{ selectedNodeSummary }}
                        </p>
                        <div
                            v-if="selectedNodeChildren.length"
                            class="knowledge-tree__detail-list"
                        >
                            <h5>Contained Passages</h5>
                            <ul>
                                <li
                                    v-for="child in selectedNodeChildren"
                                    :key="child.id"
                                >
                                    <p>{{ child.label }}</p>
                                    <small>{{ renderPassageMeta(child) }}</small>
                                </li>
                            </ul>
                        </div>
                    </div>
                </section>

                <section class="knowledge-tree__section" v-if="similarityCount">
                    <h4>Similarity Links</h4>
                    <p class="knowledge-tree__note">
                        {{ similarityCount }} similarity edges connect related passages.
                    </p>
                </section>
            </div>
        </template>
        <template #modal-actions>
            <EscrButton
                color="text"
                :on-click="downloadJson"
                label="Download JSON"
            />
            <EscrButton
                color="secondary"
                :on-click="onClose"
                label="Close"
            />
        </template>
    </EscrModal>
</template>

<script>
import EscrModal from "../Modal/Modal.vue";
import EscrButton from "../Button/Button.vue";
import "./KnowledgeTreeModal.css";

export default {
    name: "KnowledgeTreeModal",
    components: {
        EscrModal,
        EscrButton,
    },
    props: {
        visible: {
            type: Boolean,
            default: false,
        },
        data: {
            type: Object,
            required: true,
        },
        onClose: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            selectedClusterId: null,
            selectedPassageId: null,
        };
    },
    computed: {
        summaryLine() {
            return `Generated ${this.passageCount} passages across ${this.clusterCount} clusters.`;
        },
        nodes() {
            const graph = this.data && this.data.graph;
            return (graph && Array.isArray(graph.nodes)) ? graph.nodes : [];
        },
        edges() {
            const graph = this.data && this.data.graph;
            return (graph && Array.isArray(graph.edges)) ? graph.edges : [];
        },
        clusters() {
            return this.nodes.filter((node) => node.type === "cluster");
        },
        clusterMembers() {
            const members = {};
            const passageMap = this.nodes
                .filter((node) => node.type === "passage")
                .reduce((acc, node) => {
                    acc[node.id] = node;
                    return acc;
                }, {});

            this.edges
                .filter((edge) => edge.type === "membership")
                .forEach((edge) => {
                    const target = passageMap[edge.target];
                    if (!target) return;
                    if (!members[edge.source]) {
                        members[edge.source] = [];
                    }
                    members[edge.source].push(target);
                });

            // keep snippets short
            Object.values(members).forEach((list) => {
                list.sort((a, b) => {
                    const orderA = (a.meta && typeof a.meta.order === "number") ? a.meta.order : 0;
                    const orderB = (b.meta && typeof b.meta.order === "number") ? b.meta.order : 0;
                    return orderA - orderB;
                });
            });

            return members;
        },
        similarityCount() {
            return this.edges.filter((edge) => edge.type === "similarity").length;
        },
        projectName() {
            return this.data && this.data.project && this.data.project.name
                ? this.data.project.name
                : "–";
        },
        hasDocument() {
            return Boolean(this.data && this.data.document && this.data.document.name);
        },
        documents() {
            return Array.isArray(this.data && this.data.documents) ? this.data.documents : [];
        },
        parts() {
            return Array.isArray(this.data && this.data.parts) ? this.data.parts : [];
        },
        passageCount() {
            const stats = this.data && this.data.graph && this.data.graph.statistics;
            return stats && typeof stats.passages === "number" ? stats.passages : 0;
        },
        clusterCount() {
            const stats = this.data && this.data.graph && this.data.graph.statistics;
            return stats && typeof stats.clusters === "number" ? stats.clusters : 0;
        },
        treeData() {
            return this.clusters.map((cluster) => ({
                id: cluster.id,
                label: cluster.label || (cluster.meta && cluster.meta.title) || `Cluster ${cluster.meta && typeof cluster.meta.index === "number" ? cluster.meta.index + 1 : cluster.id}`,
                meta: cluster.meta || {},
                passages: (this.clusterMembers[cluster.id] || []).map((member) => ({
                    ...member,
                    parentId: cluster.id,
                })),
            }));
        },
        selectedCluster() {
            if (!this.selectedClusterId) return null;
            return this.treeData.find((cluster) => cluster.id === this.selectedClusterId) || null;
        },
        selectedPassage() {
            if (!this.selectedCluster) return null;
            if (!this.selectedPassageId) return null;
            return this.selectedCluster.passages.find((passage) => passage.id === this.selectedPassageId) || null;
        },
        selectedNode() {
            return this.selectedPassage || this.selectedCluster;
        },
        selectedNodeTitle() {
            if (!this.selectedNode) return "";
            if (this.selectedPassage) {
                return this.selectedPassage.label || "Passage";
            }
            return this.selectedCluster.label || "Cluster";
        },
        selectedNodeMeta() {
            if (!this.selectedNode) return "";
            if (this.selectedPassage) {
                return this.renderPassageMeta(this.selectedPassage);
            }
            const size = this.selectedCluster.passages.length;
            return `${size} passage${size === 1 ? "" : "s"}`;
        },
        selectedNodeSummary() {
            if (this.selectedPassage && this.selectedPassage.label) {
                return this.selectedPassage.meta && this.selectedPassage.meta.snippet
                    ? this.selectedPassage.meta.snippet
                    : this.selectedPassage.label;
            }
            if (this.selectedCluster && this.selectedCluster.meta && this.selectedCluster.meta.summary) {
                return this.selectedCluster.meta.summary;
            }
            return "";
        },
        selectedNodeChildren() {
            if (this.selectedPassage) {
                return [];
            }
            if (this.selectedCluster) {
                return this.selectedCluster.passages;
            }
            return [];
        },
    },
    methods: {
        clusterSize(cluster) {
            if (!cluster || !cluster.meta || typeof cluster.meta.size !== "number") {
                return 0;
            }
            return cluster.meta.size;
        },
        renderPartTitle(part) {
            if (!part) return "";
            const base = part.title || `Image ${part.order + 1}`;
            return base;
        },
        renderPassageMeta(passage) {
            const meta = passage.meta || {};
            const parts = [];
            if (meta.document_name) {
                parts.push(meta.document_name);
            }
            if (typeof meta.order === "number") {
                parts.push(`#${meta.order + 1}`);
            }
            if (meta.part) {
                parts.push(`Image ${meta.part}`);
            }
            return parts.join(" · ") || "Passage";
        },
        downloadJson() {
            const blob = new Blob([JSON.stringify(this.data, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            const documentName = (this.data && this.data.document && this.data.document.name) ? this.data.document.name : null;
            const projectName = (this.data && this.data.project && this.data.project.name) ? this.data.project.name : null;
            const name = documentName || projectName || "knowledge-tree";
            link.download = `${name.replace(/\\s+/g, "-").toLowerCase()}-knowledge-tree.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        },
        selectCluster(cluster) {
            if (!cluster) return;
            this.selectedClusterId = cluster.id;
            this.selectedPassageId = null;
        },
        selectPassage(cluster, passage) {
            this.selectedClusterId = cluster.id;
            this.selectedPassageId = passage.id;
        },
        isSelectedCluster(cluster) {
            return this.selectedClusterId === cluster.id && !this.selectedPassageId;
        },
        isSelectedPassage(cluster, passage) {
            return this.selectedClusterId === cluster.id && this.selectedPassageId === passage.id;
        },
        initializeSelection() {
            if (!this.treeData.length) {
                this.selectedClusterId = null;
                this.selectedPassageId = null;
                return;
            }
            const firstCluster = this.treeData[0];
            this.selectedClusterId = firstCluster.id;
            this.selectedPassageId = firstCluster.passages.length ? firstCluster.passages[0].id : null;
        },
    },
    watch: {
        visible(newVal) {
            if (newVal) {
                this.$nextTick(() => this.initializeSelection());
            }
        },
        treeData: {
            handler() {
                this.initializeSelection();
            },
            deep: true,
        },
    },
};
</script>

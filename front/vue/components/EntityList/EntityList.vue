<template>
    <section class="entity-list">
        <header class="entity-list__header">
            <h4>Entities</h4>
            <div class="entity-list__controls">
                <select
                    v-model="typeFilter"
                    title="Filter by entity type"
                >
                    <option value="__all__">All types</option>
                    <option
                        v-for="type in availableTypes"
                        :key="type"
                        :value="type"
                    >
                        {{ type }}
                    </option>
                </select>
                <input
                    v-model="searchTerm"
                    type="search"
                    placeholder="Search text…"
                >
            </div>
        </header>

        <div class="entity-list__actions">
            <button
                type="button"
                class="entity-list__button"
                :disabled="selection.length === 0 || disabled"
                @click="$emit('accept-selected')"
            >
                Accept
            </button>
            <button
                type="button"
                class="entity-list__button entity-list__button--danger"
                :disabled="selection.length === 0 || disabled"
                @click="$emit('delete-selected')"
            >
                Delete
            </button>
            <button
                v-if="selection.length"
                type="button"
                class="entity-list__link"
                @click="$emit('clear-selection')"
            >
                Clear selection
            </button>
        </div>

        <div class="entity-list__body">
            <div
                v-if="filteredEntities.length === 0"
                class="entity-list__empty"
            >
                <p>No entities match the current filters.</p>
            </div>
            <ul
                v-else
                class="entity-list__items"
            >
                <li
                    v-for="item in filteredEntities"
                    :key="item.id"
                    :class="{
                        'entity-list__item': true,
                        'entity-list__item--active': item.id === activeId,
                        'entity-list__item--selected': selection.includes(item.id),
                    }"
                >
                    <label class="entity-list__checkbox">
                        <input
                            type="checkbox"
                            :checked="selection.includes(item.id)"
                            :disabled="disabled"
                            @change="toggleSelection(item.id)"
                        >
                    </label>
                    <button
                        class="entity-list__content"
                        type="button"
                        :title="item.text"
                        @click="$emit('select', item.id)"
                    >
                        <span class="entity-list__type">{{ item.type || "—" }}</span>
                        <span class="entity-list__text">{{ item.text || "—" }}</span>
                        <span
                            v-if="item.confidence !== null && item.confidence !== undefined"
                            class="entity-list__meta"
                        >
                            {{ (item.confidence * 100).toFixed(1) }}%
                        </span>
                        <span
                            v-if="item.status"
                            class="entity-list__status"
                        >
                            {{ item.status }}
                        </span>
                        <span class="entity-list__line">Line {{ item.lineOrder }}</span>
                    </button>
                </li>
            </ul>
        </div>
    </section>
</template>

<script>
export default {
    name: "EntityList",
    props: {
        entities: {
            type: Array,
            default: () => [],
        },
        selection: {
            type: Array,
            default: () => [],
        },
        activeId: {
            type: Number,
            default: null,
        },
        disabled: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["update:selection", "accept-selected", "delete-selected", "select", "clear-selection"],
    data() {
        return {
            typeFilter: "__all__",
            searchTerm: "",
        };
    },
    computed: {
        availableTypes() {
            const types = new Set();
            this.entities.forEach((entity) => {
                if (entity.type) types.add(entity.type);
            });
            return Array.from(types).sort();
        },
        filteredEntities() {
            return this.entities.filter((entity) => {
                const matchesType =
                    this.typeFilter === "__all__" || entity.type === this.typeFilter;
                const matchesSearch =
                    !this.searchTerm ||
                    (entity.text && entity.text.toLowerCase().includes(this.searchTerm.toLowerCase()));
                return matchesType && matchesSearch;
            });
        },
    },
    methods: {
        toggleSelection(id) {
            const next = this.selection.includes(id)
                ? this.selection.filter((item) => item !== id)
                : [...this.selection, id];
            this.$emit("update:selection", next);
        },
    },
};
</script>

<style scoped>
.entity-list {
    display: flex;
    flex-direction: column;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px;
    background-color: #ffffff;
    min-height: 220px;
}

.entity-list__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    gap: 12px;
}

.entity-list__header h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
}

.entity-list__controls {
    display: flex;
    gap: 8px;
    align-items: center;
}

.entity-list__controls select,
.entity-list__controls input {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 14px;
}

.entity-list__actions {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
}

.entity-list__button {
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    background-color: #2563eb;
    color: #ffffff;
    font-size: 14px;
    cursor: pointer;
}

.entity-list__button:disabled {
    background-color: #93c5fd;
    cursor: not-allowed;
}

.entity-list__button--danger {
    background-color: #ef4444;
}

.entity-list__button--danger:disabled {
    background-color: #fca5a5;
}

.entity-list__link {
    border: none;
    background: none;
    padding: 0;
    color: #2563eb;
    cursor: pointer;
    font-size: 13px;
}

.entity-list__body {
    flex: 1;
    overflow-y: auto;
}

.entity-list__empty {
    color: #6b7280;
    font-size: 14px;
}

.entity-list__items {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.entity-list__item {
    display: flex;
    align-items: stretch;
    border: 1px solid transparent;
    border-radius: 6px;
    transition: background-color 0.15s ease, border-color 0.15s ease;
}

.entity-list__item--active {
    border-color: #2563eb;
}

.entity-list__item--selected {
    background-color: #dbeafe;
}

.entity-list__checkbox {
    display: flex;
    align-items: center;
    padding: 8px;
}

.entity-list__content {
    flex: 1;
    text-align: left;
    border: none;
    background: none;
    padding: 8px 12px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
}

.entity-list__type {
    font-weight: 600;
    font-size: 13px;
    color: #111827;
}

.entity-list__text {
    font-size: 13px;
    color: #1f2937;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    width: 100%;
}

.entity-list__meta {
    font-size: 12px;
    color: #6b7280;
}

.entity-list__status {
    font-size: 12px;
    color: #059669;
    text-transform: uppercase;
}

.entity-list__line {
    font-size: 12px;
    color: #6b7280;
}
</style>

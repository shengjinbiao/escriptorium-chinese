<template>
    <section class="entity-inspector">
        <header class="entity-inspector__header">
            <h4>Entity Inspector</h4>
            <button
                v-if="entity"
                class="entity-inspector__close"
                type="button"
                title="Clear selection"
                @click="$emit('clear')"
            >
                ×
            </button>
        </header>
        <div
            v-if="!entity"
            class="entity-inspector__empty"
        >
            <p>Select a highlighted entity to review its details.</p>
        </div>
        <form
            v-else
            class="entity-inspector__form"
            @submit.prevent="handleSave"
        >
            <div class="entity-inspector__section">
                <label class="entity-inspector__label">Text</label>
                <p class="entity-inspector__text">
                    {{ entity.text || "—" }}
                </p>
            </div>

            <div class="entity-inspector__section">
                <label class="entity-inspector__label" for="entity-type">Entity Type</label>
                <select
                    id="entity-type"
                    v-model="form.type"
                    :disabled="disabled"
                >
                    <option
                        v-for="option in entityTypeOptions"
                        :key="option"
                        :value="option"
                    >
                        {{ option }}
                    </option>
                </select>
            </div>

            <div class="entity-inspector__section">
                <label class="entity-inspector__label" for="entity-normalized">Normalized Value</label>
                <input
                    id="entity-normalized"
                    v-model="form.normalizedValue"
                    :disabled="disabled"
                    maxlength="256"
                    type="text"
                >
            </div>

            <div class="entity-inspector__section">
                <label class="entity-inspector__label" for="entity-attributes">Attributes (JSON)</label>
                <textarea
                    id="entity-attributes"
                    v-model="form.attributes"
                    :class="{ 'entity-inspector__textarea--invalid': !attributesValid }"
                    :disabled="disabled"
                    maxlength="256"
                    rows="3"
                ></textarea>
                <small
                    v-if="!attributesValid"
                    class="entity-inspector__note entity-inspector__note--error"
                >
                    Attributes must be a valid JSON object.
                </small>
            </div>

            <div class="entity-inspector__section">
                <label class="entity-inspector__label" for="entity-confidence">Confidence</label>
                <input
                    id="entity-confidence"
                    v-model="form.confidence"
                    :disabled="disabled"
                    max="1"
                    min="0"
                    step="0.001"
                    type="number"
                >
            </div>

            <div class="entity-inspector__actions">
                <button
                    class="entity-inspector__button entity-inspector__button--danger"
                    type="button"
                    :disabled="disabled"
                    @click="handleDelete"
                >
                    Delete
                </button>
                <button
                    class="entity-inspector__button entity-inspector__button--primary"
                    type="submit"
                    :disabled="disabled || !attributesValid"
                >
                    Save Changes
                </button>
            </div>
        </form>
    </section>
</template>

<script>
export default {
    name: "EntityInspector",
    props: {
        entity: {
            type: Object,
            default: null,
        },
        entityTypeOptions: {
            type: Array,
            default: () => [],
        },
        disabled: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["save", "delete", "clear"],
    data() {
        return {
            form: {
                type: "",
                normalizedValue: "",
                attributes: "",
                confidence: "",
            },
        };
    },
    computed: {
        attributesValid() {
            if (!this.form.attributes) return true;
            try {
                const parsed = JSON.parse(this.form.attributes);
                return parsed && typeof parsed === "object" && !Array.isArray(parsed);
            } catch (error) {
                return false;
            }
        },
    },
    watch: {
        entity: {
            handler(newEntity) {
                if (!newEntity) {
                    this.form = {
                        type: "",
                        normalizedValue: "",
                        attributes: "",
                        confidence: "",
                    };
                    return;
                }
                this.form = {
                    type: newEntity.type || "",
                    normalizedValue: newEntity.normalizedValue || "",
                    attributes: newEntity.attributes || "",
                    confidence: newEntity.confidence != null ? newEntity.confidence : "",
                };
            },
            immediate: true,
        },
    },
    methods: {
        handleSave() {
            if (!this.entity || this.disabled || !this.attributesValid) return;
            this.$emit("save", {
                type: this.form.type,
                normalizedValue: this.form.normalizedValue,
                attributes: this.form.attributes,
                confidence: this.form.confidence,
            });
        },
        handleDelete() {
            if (!this.entity || this.disabled) return;
            this.$emit("delete");
        },
    },
};
</script>

<style scoped>
.entity-inspector {
    display: flex;
    flex-direction: column;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px;
    background-color: #ffffff;
    min-height: 220px;
}

.entity-inspector__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}

.entity-inspector__header h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
}

.entity-inspector__close {
    background: none;
    border: none;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
    color: #6b7280;
}

.entity-inspector__empty {
    color: #6b7280;
    font-size: 14px;
}

.entity-inspector__form {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.entity-inspector__section {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.entity-inspector__label {
    font-size: 12px;
    font-weight: 600;
    color: #4b5563;
    text-transform: uppercase;
}

.entity-inspector__text {
    margin: 0;
    font-size: 14px;
    color: #111827;
    white-space: pre-wrap;
    word-break: break-word;
}

select,
input,
textarea {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 14px;
    color: #111827;
}

textarea {
    resize: vertical;
}

.entity-inspector__textarea--invalid {
    border-color: #ef4444;
}

.entity-inspector__note {
    font-size: 12px;
    color: #6b7280;
}

.entity-inspector__note--error {
    color: #ef4444;
}

.entity-inspector__actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 8px;
}

.entity-inspector__button {
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 14px;
    cursor: pointer;
}

.entity-inspector__button--primary {
    background-color: #2563eb;
    color: #ffffff;
}

.entity-inspector__button--primary:disabled {
    background-color: #93c5fd;
    cursor: not-allowed;
}

.entity-inspector__button--danger {
    background-color: #ef4444;
    color: #ffffff;
}

.entity-inspector__button--danger:disabled {
    background-color: #fca5a5;
    cursor: not-allowed;
}
</style>

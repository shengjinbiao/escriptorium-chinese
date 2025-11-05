<template>
    <section class="entity-inspector">
        <header class="entity-inspector__header">
            <div class="entity-inspector__title">
                <h4>实体检查器</h4>
            </div>
            <button
                v-if="entity"
                class="entity-inspector__close"
                type="button"
                title="清除选择"
                @click="$emit('clear')"
            >
                ×
            </button>
        </header>

        <div v-if="!entity" class="entity-inspector__empty">
            <p>选择高亮的实体以查看详情</p>
        </div>

        <form v-else class="entity-inspector__form" @submit.prevent="handleSave">
            <div class="entity-inspector__section">
                <div class="entity-type-badge" :style="getTypeStyle(form.type)">
                    {{ getTypeLabel(form.type) }}
                </div>
                <label class="entity-inspector__label">原文</label>
                <p class="entity-inspector__text">
                    {{ entity.text || "—" }}
                </p>
            </div>

            <div class="entity-inspector__section">
                <label class="entity-inspector__label" for="entity-type">实体类型</label>
                <select
                    id="entity-type"
                    v-model="form.type"
                    :disabled="disabled"
                    class="form-control form-control-sm"
                >
                    <option
                        v-for="type in entityTypes"
                        :key="type.id"
                        :value="type.id"
                    >
                        {{ type.name }}
                    </option>
                </select>
            </div>

            <div class="entity-inspector__section">
                <label class="entity-inspector__label" for="entity-normalized">标准化值</label>
                <input
                    id="entity-normalized"
                    v-model="form.normalizedValue"
                    :disabled="disabled"
                    maxlength="256"
                    type="text"
                    class="form-control form-control-sm"
                >
            </div>

            <div class="entity-inspector__section">
                <label class="entity-inspector__label">置信度</label>
                <div class="confidence-slider">
                    <input 
                        type="range" 
                        v-model.number="form.confidence"
                        :disabled="disabled"
                        min="0"
                        max="1"
                        step="0.01"
                    />
                    <span>{{ (form.confidence * 100).toFixed(0) }}%</span>
                </div>
            </div>

            <div class="entity-inspector__section">
                <label class="entity-inspector__label" for="entity-attributes">属性</label>
                <textarea
                    id="entity-attributes"
                    v-model="form.attributes"
                    :class="{ 'entity-inspector__textarea--invalid': !attributesValid }"
                    :disabled="disabled"
                    maxlength="256"
                    rows="3"
                    class="form-control form-control-sm"
                ></textarea>
                <small
                    v-if="!attributesValid"
                    class="entity-inspector__note entity-inspector__note--error"
                >
                    属性必须是有效的JSON对象
                </small>
            </div>

            <div class="entity-inspector__status" v-if="form.status">
                <span :class="'status-badge status-' + form.status">
                    {{ getStatusLabel(form.status) }}
                </span>
                <small v-if="form.reviewedAt" class="text-muted">
                    {{ new Date(form.reviewedAt).toLocaleString() }}
                </small>
            </div>

            <div class="entity-inspector__actions">
                <button
                    type="button"
                    class="btn btn-sm btn-success"
                    :disabled="disabled"
                    @click="handleAccept"
                >
                    确认
                </button>
                <button
                    type="button"
                    class="btn btn-sm btn-danger"
                    :disabled="disabled"
                    @click="handleReject"
                >
                    拒绝
                </button>
                <button
                    type="button" 
                    class="btn btn-sm btn-outline-danger"
                    :disabled="disabled"
                    @click="handleDelete"
                >
                    删除
                </button>
            </div>
        </form>
    </section>
</template>

<script>
import { mapState } from 'vuex';
import { debounce } from 'lodash';

export default {
    name: "EntityInspector",
    props: {
        entity: {
            type: Object,
            default: null,
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
                confidence: 0,
                status: "",
                reviewedAt: null
            },
        };
    },
    computed: {
        ...mapState('entities', [
            'entityTypes'
        ]),
        
        attributesValid() {
            if (!this.form.attributes) return true;
            try {
                const parsed = JSON.parse(this.form.attributes);
                return parsed && typeof parsed === "object" && !Array.isArray(parsed);
            } catch (error) {
                return false;
            }
        }
    },
    watch: {
        entity: {
            handler(newEntity) {
                if (!newEntity) {
                    this.form = {
                        type: "",
                        normalizedValue: "",
                        attributes: "",
                        confidence: 0,
                        status: "",
                        reviewedAt: null
                    };
                    return;
                }
                
                this.form = {
                    type: newEntity.type || "",
                    normalizedValue: newEntity.normalizedValue || "",
                    attributes: newEntity.attributes || "",
                    confidence: newEntity.confidence != null ? newEntity.confidence : 0,
                    status: newEntity.status || "",
                    reviewedAt: newEntity.reviewedAt || null
                };
            },
            immediate: true,
        },
    },
    methods: {
        getTypeStyle(typeId) {
            const type = this.entityTypes.find(t => t.id === typeId);
            return type ? {
                backgroundColor: type.color,
                color: 'white'
            } : null;
        },

        getTypeLabel(typeId) {
            const type = this.entityTypes.find(t => t.id === typeId);
            return type ? type.name : typeId;
        },

        getStatusLabel(status) {
            const labels = {
                'accepted': '已确认',
                'rejected': '已拒绝',
                'pending': '待审核'
            };
            return labels[status] || status;
        },

        handleSave: debounce(function() {
            if (!this.entity || this.disabled || !this.attributesValid) return;
            
            this.$emit("save", {
                ...this.form,
                attributes: this.form.attributes ? JSON.parse(this.form.attributes) : {}
            });
        }, 300),

        async handleAccept() {
            if (!this.entity || this.disabled) return;
            
            await this.$emit("save", {
                ...this.form,
                status: 'accepted',
                reviewedAt: new Date().toISOString(),
                attributes: {
                    ...(this.form.attributes ? JSON.parse(this.form.attributes) : {}),
                    reviewed: true
                }
            });
        },

        async handleReject() {
            if (!this.entity || this.disabled) return;
            
            await this.$emit("save", {
                ...this.form,
                status: 'rejected',
                reviewedAt: new Date().toISOString(),
                attributes: {
                    ...(this.form.attributes ? JSON.parse(this.form.attributes) : {}),
                    reviewed: true
                }
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

    &__header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 16px;
    }

    &__title {
        flex: 1;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;

        h4 {
            margin: 0;
            font-size: 1.1rem;
            font-weight: 600;
        }
    }

    &__close {
        background: none;
        border: none;
        color: #666;
        font-size: 1.2rem;
        padding: 0 4px;
        cursor: pointer;

        &:hover {
            color: #333;
        }
    }

    &__empty {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 150px;
        color: #666;
    }

    &__section {
        margin-bottom: 16px;
    }

    &__label {
        display: block;
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 4px;
    }

    &__text {
        font-size: 1rem;
        margin: 0;
        padding: 8px;
        background-color: #f9fafb;
        border-radius: 4px;
    }

    &__textarea {
        &--invalid {
            border-color: #ef4444 !important;
        }
    }

    &__note {
        display: block;
        font-size: 0.8rem;
        margin-top: 4px;

        &--error {
            color: #ef4444;
        }
    }

    .entity-type-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.9rem;
        margin-bottom: 8px;
    }

    .confidence-slider {
        display: flex;
        align-items: center;
        gap: 12px;

        input[type="range"] {
            flex: 1;
        }

        span {
            min-width: 48px;
            text-align: right;
            font-size: 0.9rem;
            color: #666;
        }
    }

    &__status {
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;

        .status-badge {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;

            &.status-accepted {
                background-color: #d9f7be;
                color: #389e0d;
            }

            &.status-rejected {
                background-color: #fff1f0;
                color: #cf1322;
            }

            &.status-pending {
                background-color: #e6f7ff;
                color: #1890ff;
            }
        }

        .text-muted {
            color: #666;
            font-size: 0.8rem;
        }
    }

    &__actions {
        display: flex;
        gap: 8px;
        margin-top: 24px;
        
        .btn {
            flex: 1;
        }
    }
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

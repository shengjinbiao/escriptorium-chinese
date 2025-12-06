&lt;template>
    &lt;div class="key-value-editor">
        &lt;div 
            v-for="(pair, index) in localPairs" 
            :key="index"
            class="key-value-pair"
        >
            &lt;input
                v-model="pair.key"
                type="text"
                class="form-control form-control-sm key-input"
                placeholder="键"
                :disabled="disabled"
                @input="updateValue"
            >
            &lt;input
                v-model="pair.value"
                type="text"
                class="form-control form-control-sm value-input"
                placeholder="值"
                :disabled="disabled"
                @input="updateValue"
            >
            &lt;button
                type="button"
                class="btn btn-sm btn-outline-danger remove-btn"
                :disabled="disabled"
                @click="removePair(index)"
            >
                ×
            &lt;/button>
        &lt;/div>
        
        &lt;button
            type="button"
            class="btn btn-sm btn-outline-secondary add-btn"
            :disabled="disabled"
            @click="addPair"
        >
            添加属性
        &lt;/button>
    &lt;/div>
&lt;/template>

&lt;script>
export default {
    name: 'KeyValueEditor',
    
    props: {
        value: {
            type: [String, Object],
            default: ''
        },
        disabled: {
            type: Boolean,
            default: false
        }
    },
    
    data() {
        return {
            localPairs: []
        };
    },
    
    watch: {
        value: {
            immediate: true,
            handler(newValue) {
                if (!newValue) {
                    this.localPairs = [{key: '', value: ''}];
                    return;
                }
                
                let pairs;
                if (typeof newValue === 'string') {
                    try {
                        pairs = JSON.parse(newValue);
                    } catch (e) {
                        pairs = {};
                    }
                } else {
                    pairs = newValue;
                }
                
                this.localPairs = Object.entries(pairs).map(([key, value]) => ({
                    key,
                    value: String(value)
                }));
                
                if (!this.localPairs.length) {
                    this.localPairs = [{key: '', value: ''}];
                }
            }
        }
    },
    
    methods: {
        addPair() {
            this.localPairs.push({key: '', value: ''});
        },
        
        removePair(index) {
            this.localPairs.splice(index, 1);
            if (!this.localPairs.length) {
                this.localPairs = [{key: '', value: ''}];
            }
            this.updateValue();
        },
        
        updateValue() {
            const obj = {};
            this.localPairs.forEach(pair => {
                if (pair.key && pair.value) {
                    obj[pair.key] = pair.value;
                }
            });
            this.$emit('input', JSON.stringify(obj));
        }
    }
};
&lt;/script>

&lt;style lang="scss" scoped>
.key-value-editor {
    .key-value-pair {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
        
        .key-input,
        .value-input {
            flex: 1;
        }
        
        .remove-btn {
            padding: 0 8px;
        }
    }
    
    .add-btn {
        width: 100%;
    }
}
&lt;/style>
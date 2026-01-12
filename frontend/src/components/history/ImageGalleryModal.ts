import { ref, computed } from 'vue'
import { generateContent, updateHistory, type Page } from '../../api'

/**
 * 图片画廊模态框组件
 *
 * 功能：
 * - 展示历史记录的所有生成图片
 * - 支持重新生成单张图片
 * - 支持下载单张/全部图片
 * - 可展开查看完整大纲
 * - 可查看生成的内容（标题、文案、标签）
 */

// 定义记录类型
export interface ViewingRecord {
  id: string
  title: string
  updated_at: string
  outline: {
    raw: string
    pages: Page[]
  }
  images: {
    task_id: string
    generated: string[]
  }
  content?: {
    titles: string[]
    copywriting: string
    tags: string[]
    status: 'idle' | 'generating' | 'done' | 'error'
    error?: string
  }
}

// 定义 Props
export interface ImageGalleryModalProps {
  visible: boolean
  record: ViewingRecord | null
  regeneratingImages: Set<number>
}

// 定义 Emits
export interface ImageGalleryModalEmits {
  (e: 'close'): void
  (e: 'showOutline'): void
  (e: 'downloadAll'): void
  (e: 'download', filename: string, index: number): void
  // 新增可选的 editedPage 参数，用于传递编辑后的页面内容给父组件
  (e: 'regenerate', index: number, editedPage?: { type: string; content: string }): void
}

// 标题展开状态
export const titleExpanded = ref(false)
export const showContentModal = ref(false)

// 内容生成状态
export const contentLoading = ref(false)
export const contentError = ref('')
// per-page 编辑器状态
export const editingIndex = ref<number | null>(null)
export const editingText = ref<string>('')
export const savingEdit = ref(false)

// 格式化日期
export const formattedDate = computed(() => {
  if (!props.record) return ''
  const d = new Date(props.record.updated_at)
  return `${d.getMonth() + 1}/${d.getDate()}`
})

// 格式化文案（按换行分段）
export const formattedCopywriting = computed(() => {
  if (!props.record?.content?.copywriting) return []
  return props.record.content.copywriting.split('\n').filter(p => p.trim())
})

// 检查是否有内容
export const hasContent = computed(() => {
  if (!props.record?.content) return false
  const content = props.record.content
  return (
    (content.titles && content.titles.length > 0) ||
    (content.copywriting && content.copywriting.trim()) ||
    (content.tags && content.tags.length > 0)
  )
})

// 复制到剪贴板
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      return true
    } catch {
      return false
    } finally {
      document.body.removeChild(textarea)
    }
  }
}

// 复制所有标签
export async function copyAllTags() {
  if (!props.record?.content?.tags) return
  const text = props.record.content.tags.map(t => `#${t}`).join(' ')
  await copyToClipboard(text)
}

// 打开单页编辑器
export function openPageEditor(index: number) {
  if (!props.record) return
  const page = props.record.outline.pages[index]
  editingIndex.value = index
  editingText.value = page?.content || ''
}

export function closePageEditor() {
  editingIndex.value = null
  editingText.value = ''
}

// 保存编辑并可选择是否持久化到历史并发起重新生成
export async function saveEditAndGenerate(saveToHistory: boolean) {
  if (editingIndex.value === null || !props.record) return
  const idx = editingIndex.value
  const newContent = editingText.value || ''
  // 更新本地 record（UI 即时反映）
  props.record.outline.pages[idx].content = newContent

  // 如果选择保存到历史，则调用 updateHistory
  if (saveToHistory) {
    savingEdit.value = true
    try {
      await updateHistory(props.record.id, {
        outline: {
          raw: props.record.outline.raw,
          pages: props.record.outline.pages
        }
      })
    } catch (e) {
      console.error('保存编辑到历史失败', e)
    } finally {
      savingEdit.value = false
    }
  }

  // 触发父组件的重新生成事件，传递编辑后的 page
  const editedPage = props.record.outline.pages[idx]
  // @ts-ignore - emits typing handled above
  emit('regenerate', idx, editedPage)

  closePageEditor()
}

// 重新生成内容（标题、文案、标签）
export async function regenerateContent() {
  if (!props.record) return
  
  if (contentLoading.value) return
  
  contentLoading.value = true
  contentError.value = ''

  try {
    console.log('🚀 重新生成内容...', {
      title: props.record.title,
      outlineLength: props.record.outline.raw?.length || 0
    })

    const result = await generateContent(props.record.title, props.record.outline.raw || '')

    console.log('📨 API响应:', result)

    if (result.success && result.titles && result.copywriting && result.tags) {
      console.log('✅ 内容重新生成成功:', {
        titlesCount: result.titles.length,
        copywritingLength: result.copywriting.length,
        tagsCount: result.tags.length
      })
      
      // 更新record中的内容
      if (props.record.content) {
        props.record.content.titles = result.titles
        props.record.content.copywriting = result.copywriting
        props.record.content.tags = result.tags
        props.record.content.status = 'done'
        props.record.content.error = undefined
      }
    } else {
      console.error('❌ 内容重新生成失败:', result.error)
      contentError.value = result.error || '生成失败'
    }
  } catch (error: any) {
    console.error('💥 重新生成内容异常:', error)
    contentError.value = error.message || '生成失败，请重试'
  } finally {
    contentLoading.value = false
  }
}

// 这些变量需要在组件中使用 defineProps 和 defineEmits 来定义
// 在 Vue 组件中，我们需要在 setup 函数中访问它们
let props: ImageGalleryModalProps
let emit: (e: any, ...args: any[]) => void

// 设置 props 和 emit 的函数
export function setImageGalleryModalContext(propsRef: ImageGalleryModalProps, emitRef: (e: any, ...args: any[]) => void) {
  props = propsRef
  emit = emitRef
}

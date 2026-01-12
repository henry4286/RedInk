<template>
  <!-- 图片画廊模态框 -->
  <div v-if="visible && record" class="modal-fullscreen" @click="$emit('close')">
    <div class="modal-body" @click.stop>
      <!-- 头部区域 -->
      <div class="modal-header">
        <div style="flex: 1;">
          <!-- 标题区域 -->
          <div class="title-section">
            <h3
              class="modal-title"
              :class="{ 'collapsed': !titleExpanded && record.title.length > 80 }"
            >
              {{ record.title }}
            </h3>
            <button
              v-if="record.title.length > 80"
              class="title-expand-btn"
              @click="titleExpanded = !titleExpanded"
            >
              {{ titleExpanded ? '收起' : '展开' }}
            </button>
          </div>

          <div class="modal-meta">
            <span>{{ record.outline.pages.length }} 张图片 · {{ formattedDate }}</span>
            <button
              class="view-outline-btn"
              @click="$emit('showOutline')"
              title="查看完整大纲"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
              </svg>
              查看大纲
            </button>
            <button
              v-if="record && record.content"
              class="view-outline-btn"
              @click="showContentModal = true"
              title="查看标题、文案和标签"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 0 2h7v2H4a2 2 0 0 0 0-2 2v-2a2 2 0 0 0 0 2H4a2 2 0 0 0 0-2v6a2 2 0 0 0 0 2h16a2 2 0 0 0 0-2V6a2 2 0 0 0 0-2z"></path>
                <polyline points="4 11 4 6"></polyline>
              </svg>
              查看内容
            </button>
          </div>
        </div>

        <div class="header-actions">
          <button class="btn download-btn" @click="$emit('downloadAll')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            打包下载
          </button>
          <button class="close-icon" @click="$emit('close')">×</button>
        </div>
      </div>

      <!-- 图片网格 -->
      <div class="modal-gallery-grid">
        <div
          v-for="(img, idx) in record.images.generated"
          :key="idx"
          class="modal-img-item"
        >
          <div
            class="modal-img-preview"
            v-if="img"
            :class="{ 'regenerating': regeneratingImages.has(idx) }"
          >
            <img
              :src="`/api/images/${record.images.task_id}/${img}`"
              loading="lazy"
              decoding="async"
            />
            <div class="modal-img-overlay">
              <div style="display:flex; gap:8px;">
                <button
                  class="modal-overlay-btn"
                  @click.prevent="openPageEditor(idx)"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 20h9"></path>
                    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"></path>
                  </svg>
                  编辑
                </button>
                <button
                  class="modal-overlay-btn"
                  @click="$emit('regenerate', idx)"
                  :disabled="regeneratingImages.has(idx)"
                >
                  <svg class="regenerate-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 4v6h-6"></path>
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                  </svg>
                  {{ regeneratingImages.has(idx) ? '重绘中...' : '重新生成' }}
                </button>
              </div>
            </div>
          </div>
          <div class="placeholder" v-else>Waiting...</div>

          <div class="img-footer">
            <span>Page {{ idx + 1 }}</span>
            <span
              v-if="img"
              class="download-link"
              @click="$emit('download', img, idx)"
            >
              下载
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 内容显示模态框 -->
    <div v-if="showContentModal && record.content" class="modal-fullscreen" @click="showContentModal = false">
      <div class="modal-body" @click.stop style="max-width: 800px;">
        <div class="modal-header">
          <h3 style="margin: 0; font-size: 18px; font-weight: 600;">
            标题、文案和标签
          </h3>
          <button class="close-icon" @click="showContentModal = false" style="font-size: 24px;">×</button>
        </div>

        <div class="content-modal-body" style="padding: 20px; max-height: 70vh; overflow-y: auto;">
          <!-- 空内容提示 -->
          <div v-if="!hasContent" class="empty-content">
            <div class="empty-icon">📝</div>
            <h3>暂无内容</h3>
            <p>该历史记录还没有生成标题、文案和标签</p>
            <button 
              class="btn btn-primary" 
              @click="regenerateContent"
              :disabled="contentLoading"
              style="margin-top: 16px;"
            >
              {{ contentLoading ? '生成中...' : '生成内容' }}
            </button>
          </div>

          <!-- 错误提示 -->
          <div v-if="contentError" class="error-content">
            <div class="error-icon">!</div>
            <p>{{ contentError }}</p>
            <button 
              class="btn btn-secondary" 
              @click="regenerateContent"
              :disabled="contentLoading"
            >
              {{ contentLoading ? '重试中...' : '重新生成' }}
            </button>
          </div>

          <!-- 标题区域 -->
          <div class="content-card" v-if="record.content.titles && record.content.titles.length > 0">
            <div class="card-header">
              <h3>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 6h16M4 12h16M4 18h10"></path>
                </svg>
                标题
              </h3>
              <button 
                class="copy-btn" 
                @click="regenerateContent"
                :disabled="contentLoading"
                style="display: flex; align-items: center; gap: 4px;"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 4v6h-6M1 20v-6h6"></path>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                </svg>
                {{ contentLoading ? '生成中...' : '重新生成' }}
              </button>
            </div>
            <div class="titles-list">
              <div 
                v-for="(title, index) in record.content.titles" 
                :key="index" 
                class="title-item" 
                @click="copyToClipboard(title)"
              >
                <span class="title-badge">{{ index === 0 ? '推荐' : `备选${index}` }}</span>
                <span class="title-text">{{ title }}</span>
                <span class="copy-hint">点击复制</span>
              </div>
            </div>
          </div>

          <!-- 文案区域 -->
          <div class="content-card" v-if="record.content.copywriting">
            <div class="card-header">
              <h3>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0 1-2 2v16a2 2 0 0 0 0 2h12a2 2 0 0 0 2 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
                文案
              </h3>
              <button class="copy-btn" @click="copyToClipboard(record.content.copywriting)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2h9"></path>
                </svg>
                复制
              </button>
            </div>
            <div class="copywriting-content">
              <p v-for="(paragraph, index) in formattedCopywriting" :key="index">{{ paragraph }}</p>
            </div>
          </div>

          <!-- 标签区域 -->
          <div class="content-card" v-if="record.content.tags && record.content.tags.length > 0">
            <div class="card-header">
              <h3>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h2"></path>
                  <line x1="7" y1="7" x2="7.01" y2="7"></line>
                </svg>
                标签
              </h3>
              <button class="copy-btn" @click="copyAllTags">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2h9"></path>
                </svg>
                复制全部
              </button>
            </div>
            <div class="tags-list">
              <span
                v-for="(tag, index) in record.content.tags"
                :key="index"
                class="tag-item"
                @click="copyToClipboard(`#${tag}`)"
              >
                #{{ tag }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 单页编辑模态框 -->
    <div v-if="editingIndex !== null" class="modal-fullscreen" @click="closePageEditor">
      <div class="modal-body" @click.stop style="max-width:700px; height: auto; padding: 16px;">
        <div class="modal-header" style="align-items: center;">
          <h3 style="margin: 0; font-size: 16px;">编辑第 {{ (editingIndex ?? 0) + 1 }} 页的提示词 / 文案</h3>
          <button class="close-icon" @click="closePageEditor">×</button>
        </div>
        <div style="padding: 12px;">
          <textarea v-model="editingText" rows="8" style="width:100%; font-size:14px; padding:12px; border-radius:8px; border:1px solid var(--border-color);"></textarea>
          <div style="display:flex; gap:8px; justify-content:flex-end; margin-top:12px;">
            <button class="btn" @click="closePageEditor">取消</button>
            <button class="btn" :disabled="savingEdit" @click="saveEditAndGenerate(false)">仅生成</button>
            <button class="btn btn-primary" :disabled="savingEdit" @click="saveEditAndGenerate(true)">
              {{ savingEdit ? '保存中...' : '保存并生成' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { 
  titleExpanded, 
  showContentModal, 
  contentLoading, 
  contentError, 
  editingIndex, 
  editingText, 
  savingEdit, 
  formattedDate, 
  formattedCopywriting, 
  hasContent, 
  copyToClipboard, 
  copyAllTags, 
  openPageEditor, 
  closePageEditor, 
  saveEditAndGenerate, 
  regenerateContent,
  setImageGalleryModalContext,
  type ViewingRecord,
  type ImageGalleryModalProps 
} from './ImageGalleryModal'
import type { Page } from '../../api'

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

// 定义 Props
const props = defineProps<ImageGalleryModalProps>()

// 定义 Emits
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'showOutline'): void
  (e: 'downloadAll'): void
  (e: 'download', filename: string, index: number): void
  // 新增可选的 editedPage 参数，用于传递编辑后的页面内容给父组件
  (e: 'regenerate', index: number, editedPage?: Page): void
}>()

// 设置上下文
setImageGalleryModalContext(props, emit)
</script>

<style scoped>
/* 引入外部样式文件 */
@import '../../assets/css/ImageGalleryModal.css';
</style>

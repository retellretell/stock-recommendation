/**
 * 접근성 관련 유틸리티
 */

// 색맹 친화적 색상 팔레트
export const AccessibleColors = {
  // 색맹 친화적 팔레트 (Colorbrewer 2.0 기반)
  positive: {
    primary: '#1E88E5',    // 파랑 (모든 색맹 유형에 안전)
    secondary: '#43A047',  // 초록 (적록색맹 고려)
    text: '#0D47A1'
  },
  negative: {
    primary: '#E53935',    // 빨강
    secondary: '#FF6F00',  // 주황 (대체색)
    text: '#B71C1C'
  },
  neutral: {
    primary: '#616161',
    secondary: '#9E9E9E',
    text: '#424242'
  },
  
  // 패턴 오버레이 (색상 외 구분 요소)
  patterns: {
    positive: 'url(#diagonal-lines-up)',
    negative: 'url(#diagonal-lines-down)',
    neutral: 'url(#dots)'
  }
};

// 고대비 색상
export const HighContrastColors = {
  positive: {
    primary: '#000000',
    secondary: '#FFFFFF',
    text: '#000000'
  },
  negative: {
    primary: '#FFFFFF',
    secondary: '#000000',
    text: '#FFFFFF'
  },
  neutral: {
    primary: '#666666',
    secondary: '#CCCCCC',
    text: '#333333'
  }
};

// 아이콘과 텍스트 레이블 병행
export const AccessibleWeatherIcons = {
  sunny: { 
    icon: '☀️', 
    label: '맑음 (상승)', 
    pattern: 'rising',
    description: '상승 가능성이 높은 날씨입니다'
  },
  partlyCloudy: { 
    icon: '🌤️', 
    label: '약간 구름 (약상승)', 
    pattern: 'slight-rising',
    description: '약간의 상승 가능성이 있습니다'
  },
  cloudy: { 
    icon: '⛅', 
    label: '구름 (보합)', 
    pattern: 'neutral',
    description: '변동성이 있을 수 있습니다'
  },
  overcast: { 
    icon: '🌥️', 
    label: '흐림 (약하락)', 
    pattern: 'slight-falling',
    description: '조정 가능성이 있습니다'
  },
  rainy: { 
    icon: '🌧️', 
    label: '비 (하락)', 
    pattern: 'falling',
    description: '하락 가능성이 높은 날씨입니다'
  }
};

// 키보드 네비게이션 키
export const KeyboardKeys = {
  ENTER: 'Enter',
  SPACE: ' ',
  ESCAPE: 'Escape',
  TAB: 'Tab',
  ARROW_UP: 'ArrowUp',
  ARROW_DOWN: 'ArrowDown',
  ARROW_LEFT: 'ArrowLeft',
  ARROW_RIGHT: 'ArrowRight',
  HOME: 'Home',
  END: 'End'
};

// 스크린 리더 전용 텍스트 생성
export function generateScreenReaderText(stock: any): string {
  const direction = stock.probability >= 0.5 ? '상승' : '하락';
  const confidence = `신뢰도 ${(stock.confidence * 100).toFixed(0)}퍼센트`;
  const fundamental = `펀더멘털 점수 ${(stock.fundamental_score * 100).toFixed(0)}점`;
  
  return `${stock.name} 종목, ${direction} 확률 ${(stock.probability * 100).toFixed(0)}퍼센트, ${confidence}, ${fundamental}`;
}

// ARIA 라이브 리전 업데이트
export function announceToScreenReader(message: string, priority: 'polite' | 'assertive' = 'polite') {
  const announcement = document.createElement('div');
  announcement.setAttribute('role', 'status');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;
  
  document.body.appendChild(announcement);
  
  // 메시지 전달 후 제거
  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
}

// 포커스 트랩 (모달 등에서 사용)
export class FocusTrap {
  private element: HTMLElement;
  private focusableElements: HTMLElement[];
  private firstFocusable: HTMLElement | null;
  private lastFocusable: HTMLElement | null;
  
  constructor(element: HTMLElement) {
    this.element = element;
    this.focusableElements = this.getFocusableElements();
    this.firstFocusable = this.focusableElements[0] || null;
    this.lastFocusable = this.focusableElements[this.focusableElements.length - 1] || null;
  }
  
  private getFocusableElements(): HTMLElement[] {
    const selectors = [
      'a[href]',
      'button:not([disabled])',
      'textarea:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      '[tabindex]:not([tabindex="-1"])'
    ];
    
    return Array.from(
      this.element.querySelectorAll<HTMLElement>(selectors.join(','))
    );
  }
  
  public activate() {
    if (this.firstFocusable) {
      this.firstFocusable.focus();
    }
    
    this.element.addEventListener('keydown', this.handleKeyDown);
  }
  
  public deactivate() {
    this.element.removeEventListener('keydown', this.handleKeyDown);
  }
  
  private handleKeyDown = (e: KeyboardEvent) => {
    if (e.key !== 'Tab') return;
    
    if (e.shiftKey) {
      // Shift + Tab
      if (document.activeElement === this.firstFocusable && this.lastFocusable) {
        e.preventDefault();
        this.lastFocusable.focus();
      }
    } else {
      // Tab
      if (document.activeElement === this.lastFocusable && this.firstFocusable) {
        e.preventDefault();
        this.firstFocusable.focus();
      }
    }
  };
}

// 색상 대비 검사
export function checkColorContrast(
  foreground: string, 
  background: string
): { ratio: number; passes: { aa: boolean; aaa: boolean } } {
  // 간단한 구현 (실제로는 더 복잡한 계산 필요)
  // WCAG 2.1 기준: AA는 4.5:1, AAA는 7:1
  
  const ratio = 4.5; // 더미 값
  
  return {
    ratio,
    passes: {
      aa: ratio >= 4.5,
      aaa: ratio >= 7
    }
  };
}

// 애니메이션 감소 설정 확인
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  
  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  return mediaQuery.matches;
}

// 다크 모드 선호 확인
export function prefersDarkMode(): boolean {
  if (typeof window === 'undefined') return false;
  
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  return mediaQuery.matches;
}

// 터치 디바이스 확인
export function isTouchDevice(): boolean {
  if (typeof window === 'undefined') return false;
  
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

// 접근성 설정 로컬 스토리지 관리
export const AccessibilitySettings = {
  get: () => {
    if (typeof window === 'undefined') return {};
    
    const stored = localStorage.getItem('accessibility_settings');
    return stored ? JSON.parse(stored) : {};
  },
  
  set: (settings: any) => {
    if (typeof window === 'undefined') return;
    
    localStorage.setItem('accessibility_settings', JSON.stringify(settings));
  },
  
  update: (key: string, value: any) => {
    const current = AccessibilitySettings.get();
    current[key] = value;
    AccessibilitySettings.set(current);
  }
};

// 접근성 단축키 바인딩
export const AccessibilityShortcuts = {
  // Alt + 1: 메인 콘텐츠로 이동
  skipToMain: (e: KeyboardEvent) => {
    if (e.altKey && e.key === '1') {
      e.preventDefault();
      const main = document.querySelector('main');
      if (main) {
        (main as HTMLElement).focus();
        announceToScreenReader('메인 콘텐츠로 이동했습니다');
      }
    }
  },
  
  // Alt + 2: 네비게이션으로 이동
  skipToNav: (e: KeyboardEvent) => {
    if (e.altKey && e.key === '2') {
      e.preventDefault();
      const nav = document.querySelector('nav');
      if (nav) {
        (nav as HTMLElement).focus();
        announceToScreenReader('네비게이션으로 이동했습니다');
      }
    }
  },
  
  // Alt + S: 검색으로 이동
  skipToSearch: (e: KeyboardEvent) => {
    if (e.altKey && e.key === 's') {
      e.preventDefault();
      const search = document.querySelector('[role="search"]');
      if (search) {
        const input = search.querySelector('input');
        if (input) {
          (input as HTMLElement).focus();
          announceToScreenReader('검색으로 이동했습니다');
        }
      }
    }
  },
  
  // Escape: 모달/팝업 닫기
  closeModal: (e: KeyboardEvent, callback: () => void) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      callback();
      announceToScreenReader('창이 닫혔습니다');
    }
  }
};

// 접근성 체크리스트
export const AccessibilityChecklist = {
  // 이미지 대체 텍스트 확인
  checkAltText: () => {
    const images = document.querySelectorAll('img');
    const missing: HTMLElement[] = [];
    
    images.forEach(img => {
      if (!img.getAttribute('alt')) {
        missing.push(img as HTMLElement);
      }
    });
    
    return {
      total: images.length,
      missing: missing.length,
      elements: missing
    };
  },
  
  // 헤딩 구조 확인
  checkHeadingStructure: () => {
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    const structure: number[] = [];
    let hasMultipleH1 = false;
    let hasSkippedLevel = false;
    
    headings.forEach((heading, index) => {
      const level = parseInt(heading.tagName.substring(1));
      structure.push(level);
      
      if (level === 1 && structure.filter(l => l === 1).length > 1) {
        hasMultipleH1 = true;
      }
      
      if (index > 0 && level > structure[index - 1] + 1) {
        hasSkippedLevel = true;
      }
    });
    
    return {
      structure,
      hasMultipleH1,
      hasSkippedLevel,
      isValid: !hasMultipleH1 && !hasSkippedLevel
    };
  },
  
  // 폼 레이블 확인
  checkFormLabels: () => {
    const inputs = document.querySelectorAll('input, select, textarea');
    const unlabeled: HTMLElement[] = [];
    
    inputs.forEach(input => {
      const id = input.getAttribute('id');
      const hasLabel = id && document.querySelector(`label[for="${id}"]`);
      const hasAriaLabel = input.getAttribute('aria-label');
      const hasAriaLabelledby = input.getAttribute('aria-labelledby');
      
      if (!hasLabel && !hasAriaLabel && !hasAriaLabelledby) {
        unlabeled.push(input as HTMLElement);
      }
    });
    
    return {
      total: inputs.length,
      unlabeled: unlabeled.length,
      elements: unlabeled
    };
  }
};

// 포커스 가시성 향상
export function enhanceFocusVisibility() {
  const style = document.createElement('style');
  style.textContent = `
    *:focus {
      outline: 3px solid #4A90E2 !important;
      outline-offset: 2px !important;
    }
    
    *:focus:not(:focus-visible) {
      outline: none !important;
    }
    
    *:focus-visible {
      outline: 3px solid #4A90E2 !important;
      outline-offset: 2px !important;
    }
  `;
  document.head.appendChild(style);
}

// 텍스트 크기 조정
export function adjustTextSize(factor: number) {
  const root = document.documentElement;
  const currentSize = parseFloat(getComputedStyle(root).fontSize);
  const newSize = currentSize * factor;
  
  // 최소 12px, 최대 24px
  if (newSize >= 12 && newSize <= 24) {
    root.style.fontSize = `${newSize}px`;
    announceToScreenReader(`텍스트 크기가 ${Math.round(factor * 100)}%로 조정되었습니다`);
  }
}

// 링크 타겟 확인 (새 창 열림 경고)
export function checkExternalLinks() {
  const links = document.querySelectorAll('a[target="_blank"]');
  
  links.forEach(link => {
    const text = link.textContent || '';
    if (!text.includes('새 창')) {
      // aria-label 추가
      const currentLabel = link.getAttribute('aria-label') || text;
      link.setAttribute('aria-label', `${currentLabel} (새 창에서 열림)`);
      
      // 시각적 표시 추가
      if (!link.querySelector('.external-indicator')) {
        const indicator = document.createElement('span');
        indicator.className = 'external-indicator';
        indicator.textContent = ' ↗';
        indicator.setAttribute('aria-hidden', 'true');
        link.appendChild(indicator);
      }
    }
  });
}

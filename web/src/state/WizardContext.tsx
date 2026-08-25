import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

export type Gender = 'male' | 'female' | 'any'

/**
 * 연령대 한 줄.
 *
 * 화면이 남/여/상관없음 3칸 입력에서 "총 인원 + 비율 슬라이더"로 바뀌었다(Figma 130:13839).
 * 그래서 저장하는 값도 성별 인원 3개가 아니라 총원 하나와 비율 하나다 —
 * 인원은 비율에서 파생되므로, 둘 다 들고 있으면 반드시 어긋난다.
 */
export type AgeRow = {
  id: string
  label: string
  enabled: boolean
  /** 이 연령대의 총 인원 */
  total: number
  /** 여성 비율 0~100. 나머지가 남성이다. genderAgnostic 이면 무시된다. */
  femalePercent: number
  /** 성별을 지정하지 않고 무작위 배정 */
  genderAgnostic: boolean
}

export const GENDERS: { key: Gender; label: string }[] = [
  { key: 'male', label: '남성' },
  { key: 'female', label: '여성' },
  { key: 'any', label: '상관없음' },
]

const DEFAULT_ROWS: AgeRow[] = [
  { id: '10s', label: '10대', enabled: true, total: 10, femalePercent: 50, genderAgnostic: false },
  { id: '20s', label: '20대', enabled: true, total: 40, femalePercent: 60, genderAgnostic: false },
  { id: '30s', label: '30대', enabled: true, total: 30, femalePercent: 30, genderAgnostic: false },
  { id: '40s', label: '40대', enabled: true, total: 15, femalePercent: 60, genderAgnostic: false },
  { id: '50s', label: '50대', enabled: true, total: 5, femalePercent: 50, genderAgnostic: true },
  { id: '60s', label: '60대 이상', enabled: false, total: 0, femalePercent: 50, genderAgnostic: false },
]

/** 총원과 비율에서 실제 인원을 만든다. 반올림 오차는 남성 쪽이 흡수한다. */
export function splitRow(row: AgeRow): { male: number; female: number; any: number } {
  if (!row.enabled) return { male: 0, female: 0, any: 0 }
  if (row.genderAgnostic) return { male: 0, female: 0, any: row.total }
  const female = Math.round((row.total * row.femalePercent) / 100)
  return { female, male: row.total - female, any: 0 }
}

type WizardState = {
  /** 서버에 만들어진 테스트 id. 1단계에서 생성되고 이후 단계가 이 id로 저장한다. */
  testId: string | null
  setTestId: (value: string | null) => void
  testName: string
  setTestName: (value: string) => void
  device: string
  setDevice: (value: string) => void
  link: string
  setLink: (value: string) => void
  mission: string
  setMission: (value: string) => void
  successCriteria: string
  setSuccessCriteria: (value: string) => void
  rows: AgeRow[]
  setRows: (updater: (prev: AgeRow[]) => AgeRow[]) => void
  /**
   * 링크를 자동으로 채워 넣은 프로젝트. 이 표시가 컴포넌트가 아니라 여기 있는 이유는,
   * 마법사 단계를 오갈 때 화면이 매번 다시 만들어지기 때문이다. 화면 안에 두면
   * 2단계에서 1단계로 돌아올 때마다 사용자가 고쳐 놓은 주소를 도로 덮어쓴다.
   */
  seededProjectId: string | null
  markSeeded: (projectId: string) => void
  /** 새 테스트를 처음부터 시작한다. 앞선 테스트의 이름·미션이 남아 있으면 안 된다. */
  resetTest: () => void
  /** 활성화된 연령대만 합산한 총 인원 */
  totalPersonas: number
  countByGender: (gender: Gender) => number
  rowTotal: (row: AgeRow) => number
}

const WizardContext = createContext<WizardState | null>(null)

export function WizardProvider({ children }: { children: ReactNode }) {
  const [testId, setTestId] = useState<string | null>(null)
  const [testName, setTestName] = useState('')
  // DeviceSelect 의 프리셋 id. 기본값은 기획서의 답사 환경(1280×800).
  const [device, setDevice] = useState('laptop-1280')
  const [link, setLink] = useState('')
  const [mission, setMission] = useState('')
  // 성공 기준은 미션에서 자동으로 만들어진다. 사용자가 직접 쓰는 값이 아니다.
  const [successCriteria, setSuccessCriteria] = useState('')
  const [rows, setRows] = useState<AgeRow[]>(DEFAULT_ROWS)
  const [seededProjectId, setSeededProjectId] = useState<string | null>(null)

  const value = useMemo<WizardState>(() => {
    const rowTotal = (row: AgeRow) => (row.enabled ? row.total : 0)

    return {
      testId,
      setTestId,
      testName,
      setTestName,
      device,
      setDevice,
      link,
      setLink,
      mission,
      setMission,
      successCriteria,
      setSuccessCriteria,
      rows,
      setRows: (updater) => setRows((prev) => updater(prev)),
      seededProjectId,
      markSeeded: setSeededProjectId,
      resetTest: () => {
        setTestId(null)
        setTestName('')
        setLink('')
        setMission('')
        setSuccessCriteria('')
        setRows(DEFAULT_ROWS)
        // 표시를 지워야 다음 화면이 그 프로젝트의 주소를 새로 채워 넣는다.
        setSeededProjectId(null)
      },
      totalPersonas: rows.reduce((total, row) => total + rowTotal(row), 0),
      countByGender: (gender) =>
        rows.reduce((total, row) => total + splitRow(row)[gender], 0),
      rowTotal,
    }
  }, [testId, testName, device, link, mission, successCriteria, rows, seededProjectId])

  return <WizardContext.Provider value={value}>{children}</WizardContext.Provider>
}

export function useWizard() {
  const context = useContext(WizardContext)
  if (!context) throw new Error('useWizard must be used inside <WizardProvider>')
  return context
}

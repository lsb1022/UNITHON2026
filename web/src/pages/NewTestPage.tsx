import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createTest, getProject } from '../api/client'
import { useMutation, useQuery } from '../api/hooks'
import infoIcon from '../assets/icons/info.svg'
import { AppLayout, PageBody, PageHeading } from '../components/AppLayout'
import { ConnectionCard } from '../components/ConnectionCard'
import { DeviceSelect } from '../components/DeviceSelect'
import { FieldLabel, TextField } from '../components/Field'
import { PreviewModal } from '../components/PreviewModal'
import { WizardTopBar } from '../components/StepIndicator'
import { WizardFooter } from '../components/WizardFooter'
import { useConnection } from '../hooks/useConnection'
import { useWizard } from '../state/WizardContext'

export function NewTestPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const project = useQuery(() => getProject(projectId ?? ''), [projectId])
  const create = useMutation(createTest)
  const {
    testName: name,
    setTestName: setName,
    link,
    setLink,
    device,
    setDevice,
    setTestId,
    seededProjectId,
    markSeeded,
  } = useWizard()
  const [previewOpen, setPreviewOpen] = useState(false)

  const connection = useConnection()
  const { reset } = connection

  // 프로젝트를 만들 때 쓴 주소를 그대로 채운다. 화면 문구가 "이전에 설정한 주소를
  // 등록해두었어요"라고 말하므로, 비어 있으면 그 말이 거짓이 된다.
  //
  // link 는 WizardProvider(앱 루트)에 있어서 화면을 옮겨도 살아남는다. 그래서
  // "비어 있을 때만 채운다"로 두면 앞선 테스트에서 쓴 주소가 남아 있는 한 영영
  // 채워지지 않고, 심지어 다른 프로젝트의 주소가 그대로 보인다.
  // 프로젝트별로 한 번씩만 심어 준다 — 심은 뒤 사용자가 고친 값은 건드리지 않는다.
  //
  // data.id 를 반드시 확인한다. 주소창의 프로젝트가 바뀐 직후에는 아직 이전 프로젝트의
  // 응답이 들려 있는 순간이 있는데, 그때 심으면 남의 주소를 박아 놓고 "이미 심었다"고
  // 표시해 버려서 진짜 주소가 도착해도 영영 고쳐지지 않는다.
  const detail = project.data
  useEffect(() => {
    if (!detail || detail.id !== projectId) return
    if (seededProjectId === projectId) return
    markSeeded(projectId)
    setLink((detail.preview_url ?? '').replace(/^https?:\/\//, ''))
    reset()
  }, [projectId, detail, seededProjectId, markSeeded, setLink, reset])

  return (
    <AppLayout
      topBar={
        <WizardTopBar breadcrumb={{ project: project.data?.name ?? '', page: '새 테스트' }} current={1} />
      }
      footer={
        <WizardFooter
          onPrev={() => navigate(`/projects/${projectId}`)}
          onNext={async () => {
            const created = await create.run(projectId, {
              name: name.trim(),
              device,
              target_url: connection.previewUrl ?? link,
            })
            if (!created) return
            setTestId(created.id)
            navigate(`/projects/${projectId}/tests/new/mission`)
          }}
          nextLabel={create.pending ? '저장 중…' : '다음'}
          // 필수 칸이 비어 있으면 넘어가지 못한다. 이름 없는 테스트는 목록에서 못 찾고,
          // 주소 없는 테스트는 답사할 곳이 없어 실행 단계에서 빈손으로 멈춘다.
          nextDisabled={create.pending || name.trim() === '' || link.trim() === ''}
        />
      }
    >
      <PageBody>
        <div className="max-w-[1280px]">
          <PageHeading
            title={`${project.data?.name ?? ''} / 새 테스트 생성`}
            description="이 프로젝트에서 새로운 플로우를 테스트 해요"
          />

          <div className="mt-[21px] flex flex-col gap-[20px]">
            <TextField
              label="테스트 이름"
              required
              placeholder="예) 결제 화면 사용성 테스트"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={100}
            />

            <div className="flex flex-col gap-[7px]">
              <FieldLabel required>실행 환경 디바이스</FieldLabel>
              <p className="text-[16px] leading-[1.45] text-body">
                이전에 설정한 디바이스로 등록해두었어요
              </p>
              <DeviceSelect value={device} onChange={setDevice} />
            </div>

            <div className="flex flex-col gap-[7px]">
              <FieldLabel required>프로젝트 링크</FieldLabel>
              <p className="flex items-center gap-[4px] text-[16px] leading-[1.45] text-body">
                <img src={infoIcon} alt="" aria-hidden className="size-[24px]" />
                이전에 설정한 주소 등록해두었어요 혹시 연결이 안된다면 재 업로드 해주세요 자동으로
                저장됩니다
              </p>
              <TextField
                value={link}
                onChange={(event) => {
                  setLink(event.target.value)
                  connection.reset()
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') connection.run(link)
                }}
                leading={<span className="shrink-0 text-[15px] text-placeholder">https://</span>}
                trailing={
                  <button
                    type="button"
                    onClick={() => connection.run(link)}
                    disabled={link.trim() === '' || connection.state.status === 'checking'}
                    className="h-[62px] w-[160px] shrink-0 rounded-[14px] bg-main text-[20px] leading-[1.45] font-bold text-white transition-colors hover:bg-[#2872dd] disabled:cursor-not-allowed disabled:bg-[#c4d9f9]"
                  >
                    {connection.state.status === 'checking' ? '확인 중…' : '연결하기'}
                  </button>
                }
              />
            </div>

            {create.error ? (
              <p className="text-[14px] font-medium text-danger">{create.error}</p>
            ) : null}

            <ConnectionCard
              state={connection.state}
              onPreview={() => setPreviewOpen(true)}
              onRetry={() => connection.run(link)}
            />
          </div>
        </div>
      </PageBody>

      <PreviewModal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        url={connection.previewUrl}
        embeddable={connection.embeddable}
        blockReason={connection.blockReason}
      />
    </AppLayout>
  )
}

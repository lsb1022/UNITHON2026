import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../api/client'
import { useMutation } from '../api/hooks'
import apkIcon from '../assets/img/src-apk.png'
import githubIcon from '../assets/img/src-github.png'
import linkIcon from '../assets/img/src-link.png'
import { AppLayout, PageBody, PageHeading } from '../components/AppLayout'
import { CATEGORIES, CategorySelect } from '../components/CategorySelect'
import { ConnectionCard } from '../components/ConnectionCard'
import { DEVICE_PRESETS, DeviceSelect } from '../components/DeviceSelect'
import { FieldLabel, TextField } from '../components/Field'
import { FileDropZone } from '../components/FileDropZone'
import { PreviewModal } from '../components/PreviewModal'
import { SegmentedControl } from '../components/SegmentedControl'
import { WizardTopBar } from '../components/StepIndicator'
import { WizardFooter } from '../components/WizardFooter'
import { useConnection } from '../hooks/useConnection'

const SOURCES = [
  { value: 'web', label: '웹 링크', icon: <img src={linkIcon} alt="" className="size-[14px]" /> },
  { value: 'github', label: '깃허브', icon: <img src={githubIcon} alt="" className="size-[19px]" /> },
  { value: 'apk', label: 'APK 파일', icon: <img src={apkIcon} alt="" className="size-[19px]" /> },
] as const

export function NewProjectPage() {
  const navigate = useNavigate()
  const [source, setSource] = useState<(typeof SOURCES)[number]['value']>('web')
  const [name, setName] = useState('')
  const [device, setDevice] = useState(DEVICE_PRESETS[3].id) // 노트북 1280×800 — 기본 답사 환경
  const [category, setCategory] = useState<string>(CATEGORIES[0])
  const [link, setLink] = useState('')
  const [flowMap, setFlowMap] = useState<File | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)

  const connection = useConnection()
  const create = useMutation(createProject)

  return (
    <AppLayout
      topBar={<WizardTopBar breadcrumb={{ page: '새 프로젝트' }} />}
      footer={
        <WizardFooter
          onPrev={() => navigate('/projects')}
          onNext={async () => {
            const created = await create.run({
              name: name.trim(),
              category: category.trim(),
              target_url: connection.previewUrl ?? link,
              source,
              device_preset: device,
              flow_map_path: flowMap?.name ?? null,
              preview_embeddable: connection.embeddable,
            })
            if (created) navigate(`/projects/${created.id}`)
          }}
          nextLabel={create.pending ? '만드는 중…' : '생성하기'}
          // 필수 칸이 비어 있으면 넘어가지 못한다. 링크는 비었는지에 더해
          // 실제로 연결까지 확인돼야 한다 — 못 여는 주소로는 답사를 돌릴 수 없다.
          nextDisabled={
            create.pending ||
            name.trim() === '' ||
            link.trim() === '' ||
            category.trim() === '' ||
            !connection.connected
          }
        />
      }
    >
      <PageBody>
        <div className="max-w-[1280px]">
          <PageHeading
            title="어떤 화면을 테스트할까요?"
            description="링크나 파일을 연결하면 테스트 가능한 상태인지 바로 확인해요."
          />

          <SegmentedControl
            options={SOURCES}
            value={source}
            onChange={setSource}
            className="mt-[21px] w-[420px]"
          />

          <div className="mt-[17px] flex flex-col gap-[20px]">
            <TextField
              label="프로젝트 이름"
              required
              placeholder="예) 쇼핑몰 v.1"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={100}
              counter
            />

            <div className="flex flex-col gap-[7px]">
              <FieldLabel required>실행 환경 디바이스</FieldLabel>
              <DeviceSelect value={device} onChange={setDevice} />
            </div>

            <div className="flex flex-col gap-[7px]">
              <FieldLabel required>프로젝트 카테고리</FieldLabel>
              <CategorySelect value={category} onChange={setCategory} />
            </div>

            <TextField
              label="프로젝트 링크"
              required
              placeholder="www.example.com/proto/..."
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

            <ConnectionCard
              state={connection.state}
              onPreview={() => setPreviewOpen(true)}
              onRetry={() => connection.run(link)}
            />

            {create.error ? (
              <p className="text-[14px] font-medium text-danger">{create.error}</p>
            ) : null}

            <div className="flex flex-col gap-[7px]">
              <FieldLabel hint="예) sitemap.xml">유저 플로우 맵</FieldLabel>
              <p className="text-[16px] leading-[1.45] text-body">
                혹시 유저 플로우 맵이 있다면 정확도가 훨씬 올라가요
              </p>
              <FileDropZone file={flowMap} onSelect={setFlowMap} />
            </div>
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

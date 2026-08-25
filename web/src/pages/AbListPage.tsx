import { useNavigate } from 'react-router-dom'
import { listAbTests, type AbCard, type AbSide } from '../api/client'
import { useQuery } from '../api/hooks'
import moreIcon from '../assets/icons/more.svg'
import { AppLayout, PageBody } from '../components/AppLayout'
import { Button } from '../components/Button'
import { SitePreview } from '../components/SitePreview'
import { ErrorBlock, LoadingBlock } from '../components/StateView'
import { timeAgo } from '../lib/time'

/** A/B 테스트 목록 (Figma 329:24314) · 빈 상태 (336:28758). */
export function AbListPage() {
  const navigate = useNavigate()
  const list = useQuery(listAbTests, [])

  const items = list.data?.items ?? []

  return (
    <AppLayout>
      <PageBody>
        <div className="mx-auto w-full max-w-[1442px]">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-[34px] leading-[1.45] font-bold text-ink">A/B 테스트</h1>
              <p className="mt-[8px] flex flex-wrap items-center gap-[10px] text-[15px] text-subtext">
                이전에 진행한 비교 테스트를 확인하거나 새 비교를 시작해요.
                <span className="text-main">
                  이전에 진행한 프로젝트를 A 새롭게 개선한 프로젝트를 B로 구성해요.
                </span>
              </p>
            </div>
            <Button onClick={() => navigate('/ab/new')} className="w-[230px]">
              새 A/B 테스트 만들기
            </Button>
          </div>

          <div className="mt-[36px]">
            {list.loading ? <LoadingBlock label="비교 목록을 불러오는 중이에요" /> : null}
            {list.error ? <ErrorBlock message={list.error} onRetry={list.reload} /> : null}

            {!list.loading && !list.error && items.length === 0 ? (
              <button
                type="button"
                onClick={() => navigate('/ab/new')}
                className="flex h-[380px] w-full items-center justify-center rounded-[16px] border-2 border-dashed border-main/50 bg-main/[0.06] text-[20px] font-bold text-body transition-colors hover:bg-main/[0.1]"
              >
                ＋ 새 A/B 테스트 만들기
              </button>
            ) : null}

            <div className="grid grid-cols-3 gap-x-[31px] gap-y-[22px]">
              {items.map((item) => (
                <AbCardItem key={item.id} item={item} onOpen={() => navigate(`/ab/${item.id}`)} />
              ))}
            </div>
          </div>
        </div>
      </PageBody>
    </AppLayout>
  )
}

function AbCardItem({ item, onOpen }: { item: AbCard; onOpen: () => void }) {
  return (
    <article
      onClick={onOpen}
      className="flex cursor-pointer flex-col gap-[10px] rounded-[16px] border border-line bg-white p-[14px] transition-shadow hover:shadow-[0_6px_20px_rgba(0,0,0,0.06)]"
    >
      {/* A 와 B 를 나란히 둔다. 어느 쪽이 개선 전인지 글자로 못 박아 둬야
          결과를 볼 때 방향을 헷갈리지 않는다. */}
      <div className="flex gap-[10px]">
        <SideThumb tag="A" side={item.a} />
        <SideThumb tag="B" side={item.b} />
      </div>

      <div className="flex items-start justify-between px-[8px] pb-[4px]">
        <div className="flex min-w-0 flex-1 flex-col gap-[10px] break-words">
          <p className="text-[22px] leading-[1.45] font-bold text-ink">{item.name}</p>
          <p className="text-[14px] leading-[1.45] text-subtext">테스트: {item.mission}</p>
          <p className="text-[14px] text-subtext">{timeAgo(item.created_at)}</p>
        </div>
        <button
          type="button"
          aria-label={`${item.name} 더보기`}
          onClick={(event) => event.stopPropagation()}
          className="grid size-[36px] shrink-0 place-items-center rounded-full hover:bg-black/[0.04]"
        >
          <img src={moreIcon} alt="" className="size-[36px]" />
        </button>
      </div>
    </article>
  )
}

function SideThumb({ tag, side }: { tag: 'A' | 'B'; side: AbSide }) {
  return (
    <div className="min-w-0 flex-1 overflow-hidden rounded-[10px] border border-line">
      <div className="flex items-center gap-[7px] px-[10px] py-[8px]">
        <span className="text-[16px] font-bold text-main">{tag}</span>
        <span className="truncate text-[13px] font-medium text-ink">{side.name}</span>
      </div>
      <div className="h-[110px] border-t border-line">
        <SitePreview url={side.preview_url} alt={`${side.name} 미리보기`} />
      </div>
    </div>
  )
}

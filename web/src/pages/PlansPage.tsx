import { useState } from 'react'
import { getPlanTiers, type CreditPack, type PlanTier } from '../api/client'
import { useQuery } from '../api/hooks'
import { AppLayout, PageBody } from '../components/AppLayout'
import { ErrorBlock, LoadingBlock } from '../components/StateView'

/**
 * 크레딧 및 플랜 (Figma 311:21197).
 *
 * **정해진 것만 적는다.** 요금제마다 값·크레딧·열리는 기능 한 줄씩이 전부다.
 * 예전에는 "프로젝트 10개", "팀원 3명", "CSV/PDF 리포트" 같은 항목이 줄줄이
 * 있었는데 그중 어느 것도 만든 적이 없다. 요금제 화면의 목록은 약속으로 읽히고,
 * 눌러본 사람은 없는 기능을 바로 알아챈다.
 *
 * 결제도 아직 없다. 고르면 그 사실을 말하고 멈춘다.
 */
export function PlansPage() {
  const plans = useQuery(getPlanTiers, [])
  const [notice, setNotice] = useState<string | null>(null)

  const tiers = plans.data?.tiers ?? []
  const packs = plans.data?.packs ?? []

  return (
    <AppLayout>
      <PageBody>
        <div className="mx-auto w-full max-w-[1100px]">
          <h1 className="text-[32px] leading-[1.4] font-bold text-heading">크레딧 및 플랜</h1>
          <p className="mt-[10px] text-[15px] text-subtext">
            <b className="font-semibold text-ink">1크레딧당 1 페르소나 분석</b>이에요.
          </p>

          {plans.loading ? <LoadingBlock label="요금제를 불러오는 중이에요" /> : null}
          {plans.error ? <ErrorBlock message={plans.error} onRetry={plans.reload} /> : null}

          {tiers.length ? (
            <div className="mt-[28px] grid gap-[18px] md:grid-cols-3">
              {tiers.map((tier) => (
                <TierCard key={tier.id} tier={tier} onPick={setNotice} />
              ))}
            </div>
          ) : null}

          {packs.length ? (
            <section className="mt-[34px] rounded-[16px] border border-line bg-white px-[24px] py-[20px]">
              <h2 className="text-[16px] font-bold text-heading">추가 크레딧 구매</h2>
              <div className="mt-[14px] flex flex-wrap gap-[12px]">
                {packs.map((pack) => (
                  <PackChip key={pack.credits} pack={pack} onPick={setNotice} />
                ))}
              </div>
            </section>
          ) : null}

          {notice ? (
            <p
              role="status"
              className="mt-[20px] rounded-[12px] border border-line bg-white px-[18px] py-[14px] text-[14px] text-body"
            >
              {notice}
            </p>
          ) : null}
        </div>
      </PageBody>
    </AppLayout>
  )
}

function TierCard({ tier, onPick }: { tier: PlanTier; onPick: (v: string) => void }) {
  return (
    <div
      className={`flex flex-col rounded-[16px] border bg-white px-[24px] py-[26px] ${
        tier.featured ? 'border-main shadow-[0_6px_24px_rgba(31,95,216,0.10)]' : 'border-line'
      }`}
    >
      <p className="text-[15px] font-bold tracking-[0.04em] text-subtext">{tier.name}</p>
      <p className="mt-[10px] text-[30px] leading-[1.25] font-bold text-heading tabular-nums">
        {tier.price}
      </p>
      <p className="mt-[14px] text-[17px] font-semibold text-ink tabular-nums">
        {tier.credits}크레딧
      </p>
      <p className="mt-[8px] text-[14px] text-subtext">{tier.unlock}</p>

      <button
        type="button"
        onClick={() =>
          onPick(`${tier.name} 요금제는 아직 결제를 붙이지 않았어요. 지금은 고를 수만 있어요.`)
        }
        className={`mt-[22px] h-[46px] rounded-[10px] text-[15px] font-semibold transition-colors ${
          tier.featured
            ? 'bg-main text-white hover:bg-[#2872dd]'
            : 'border border-line text-heading hover:bg-black/[0.03]'
        }`}
      >
        선택하기
      </button>
    </div>
  )
}

function PackChip({ pack, onPick }: { pack: CreditPack; onPick: (v: string) => void }) {
  return (
    <button
      type="button"
      onClick={() =>
        onPick(`${pack.credits}크레딧 구매는 아직 결제를 붙이지 않았어요.`)
      }
      className="flex items-baseline gap-[10px] rounded-[10px] border border-line px-[16px] py-[11px] transition-colors hover:border-main/60 hover:bg-main/[0.03]"
    >
      <span className="text-[16px] font-bold text-heading tabular-nums">{pack.credits}크레딧</span>
      <span className="text-[15px] text-subtext tabular-nums">{pack.price}</span>
    </button>
  )
}

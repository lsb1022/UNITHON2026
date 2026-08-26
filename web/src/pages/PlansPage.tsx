import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPlanTiers, type PlanTier } from '../api/client'
import { useQuery } from '../api/hooks'
import checkMarkBlue from '../assets/icons/check-mark-blue.svg'
import { AppLayout, PageBody } from '../components/AppLayout'
import { ErrorBlock, LoadingBlock } from '../components/StateView'

/**
 * 크레딧 및 플랜 — 구독 선택.
 *
 * **화면은 시안 그대로다.** 제목·월간/연간 토글·3열 카드·강조 카드의 파란 테두리와
 * 딱지·구분선·체크 목록·하단 크레딧 바까지 바뀐 것이 없다.
 * 바뀐 것은 **적히는 값뿐**이다:
 *
 *   무료 ₩0 · 3크레딧 · 로그 확인 불가
 *   스탠다드 ₩14,900 · 100크레딧 · A/B 테스트 기능 오픈
 *   프로 ₩39,900 · 300크레딧 · 감정내면 독백 분석
 *
 * 목록에는 정해진 표에 있는 것만 올린다. 요금제의 항목은 약속으로 읽히기 때문에,
 * 만든 적 없는 기능을 채워 두면 눌러본 사람이 바로 알아챈다.
 * 결제도 아직 없다. 고르면 그 사실을 말하고 멈춘다.
 */
export function PlansPage() {
  const navigate = useNavigate()
  const tiers = useQuery(getPlanTiers, [])
  const [yearly, setYearly] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  return (
    <AppLayout>
      <PageBody>
        <div className="mx-auto w-full max-w-[1520px]">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-[34px] leading-[1.4] font-bold text-heading">
                당신에게 딱 맞는 AI검증 도우미를 선택하세요
              </h1>
              <p className="mt-[14px] text-[15px] text-muted">
                필요한 테스트 규모에 맞춰 언제든 변경할 수 있어요.
              </p>
            </div>

            {/* 월간/연간 토글. 연간을 고르면 값이 20% 깎여 보인다 — 이 계산은
                화면에서만 하고, 실제 청구 금액은 결제가 붙을 때 서버가 정한다. */}
            <div className="flex h-[40px] shrink-0 items-center rounded-full bg-track p-[4px]">
              <button
                type="button"
                onClick={() => setYearly(false)}
                className={`h-[32px] rounded-full px-[20px] text-[13px] font-semibold transition-colors ${
                  yearly ? 'text-muted' : 'bg-main text-white'
                }`}
              >
                월간
              </button>
              <button
                type="button"
                onClick={() => setYearly(true)}
                className={`h-[32px] rounded-full px-[20px] text-[13px] font-semibold transition-colors ${
                  yearly ? 'bg-main text-white' : 'text-muted'
                }`}
              >
                연간 20% 할인
              </button>
            </div>
          </div>

          {tiers.loading ? <LoadingBlock label="플랜을 불러오는 중이에요" /> : null}
          {tiers.error ? <ErrorBlock message={tiers.error} onRetry={tiers.reload} /> : null}

          {tiers.data ? (
            <>
              <div className="mt-[40px] grid grid-cols-3 gap-[24px]">
                {tiers.data.tiers.map((tier) => (
                  <TierCard
                    key={tier.id}
                    tier={tier}
                    yearly={yearly}
                    onPick={() =>
                      setNotice(
                        `${tier.name} 플랜은 결제가 붙으면 바로 시작할 수 있어요. 지금은 미리보기예요.`,
                      )
                    }
                  />
                ))}
              </div>

              {notice ? (
                <p role="status" className="mt-[18px] text-[14px] font-medium text-main">
                  {notice}
                </p>
              ) : null}

              <div className="mt-[30px] flex items-center justify-between rounded-[16px] border border-divider bg-white px-[28px] py-[24px]">
                <p className="text-[14px] text-muted">
                  1크레딧당 1 페르소나를 분석해요. 추가 크레딧은 언제든 충전할 수 있습니다.
                </p>
                <button
                  type="button"
                  onClick={() => navigate('/settings/credit')}
                  className="text-[14px] font-medium text-main hover:underline"
                >
                  크레딧 자세히 보기 →
                </button>
              </div>
            </>
          ) : null}
        </div>
      </PageBody>
    </AppLayout>
  )
}

/** ₩14,900 → 연간 20% 할인 표시. 숫자가 없는 값(₩0)은 그대로 둔다. */
function priceLabel(price: string, yearly: boolean): string {
  if (!yearly) return price
  const digits = price.replace(/[^\d]/g, '')
  if (digits === '' || Number(digits) === 0) return price
  // 100원 단위로 맞춘다. 1000원 단위로 끊으면 ₩14,900 이 ₩12,000 이 되어
  // 끝자리가 900 인 정가와 나란히 놓였을 때 다른 가격표처럼 보인다.
  const discounted = Math.round((Number(digits) * 0.8) / 100) * 100
  return `₩${discounted.toLocaleString()}`
}

function TierCard({
  tier,
  yearly,
  onPick,
}: {
  tier: PlanTier
  yearly: boolean
  onPick: () => void
}) {
  return (
    <article
      // 목록이 두 줄뿐이라 카드가 시안보다 납작해진다. 값을 채워 늘리는 대신
      // 최소 높이를 잡아 시안의 비례를 지킨다 — 없는 기능을 적을 이유는 없다.
      className={`relative flex min-h-[430px] flex-col rounded-[16px] bg-white px-[32px] pt-[34px] pb-[40px] ${
        tier.featured
          ? 'border-2 border-main shadow-[0_6px_24px_rgba(63,106,216,0.10)]'
          : 'border border-divider'
      }`}
    >
      {tier.badge ? (
        <span className="absolute top-[22px] right-[24px] inline-flex h-[26px] items-center rounded-full bg-main px-[13px] text-[11px] font-semibold text-white">
          {tier.badge}
        </span>
      ) : null}

      <h2 className="text-[20px] font-bold text-heading">{tier.name}</h2>
      <p className="mt-[10px] text-[13px] text-muted">{tier.tagline}</p>

      <p className="mt-[30px] flex items-end gap-[8px]">
        <span className="text-[32px] leading-none font-bold text-heading tabular-nums">
          {priceLabel(tier.price, yearly)}
        </span>
        <span className="pb-[3px] text-[13px] text-muted">/ 월</span>
      </p>

      <button
        type="button"
        onClick={onPick}
        className={`mt-[26px] h-[46px] rounded-[10px] text-[14px] font-semibold transition-colors ${
          tier.featured
            ? 'bg-main text-white hover:bg-[#2872dd]'
            : 'border border-divider bg-white text-heading hover:bg-black/[0.02]'
        }`}
      >
        {tier.cta}
      </button>

      {/* 값과 목록을 가르는 선. 시안에 있는 그대로다. */}
      <ul className="mt-[28px] flex flex-col gap-[26px] border-t border-divider pt-[28px]">
        {tier.features.map((feature) => (
          <li key={feature} className="flex items-center gap-[13px]">
            <img src={checkMarkBlue} alt="" className="size-[13px]" />
            <span className="text-[13px] text-muted">{feature}</span>
          </li>
        ))}
        {/* 안 되는 것에는 체크를 달지 않는다. 파란 체크가 붙으면
            "로그 확인 불가"가 제공되는 기능처럼 읽힌다. */}
        {tier.limits.map((limit) => (
          <li key={limit} className="flex items-center gap-[13px]">
            <span
              aria-hidden
              className="flex size-[13px] items-center justify-center text-[13px] leading-none text-[#b0b8c1]"
            >
              ×
            </span>
            <span className="text-[13px] text-[#b0b8c1]">{limit}</span>
          </li>
        ))}
      </ul>
    </article>
  )
}

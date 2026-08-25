import { useNavigate } from 'react-router-dom'
import { getPlan } from '../api/client'
import { useQuery } from '../api/hooks'
import checkMarkBlue from '../assets/icons/check-mark-blue.svg'
import { SettingsCard, SettingsLayout } from '../components/SettingsLayout'
import { ErrorBlock, LoadingBlock } from '../components/StateView'

/** 설정 · 플랜 (Figma 336:28072). */
export function SettingsPlanPage() {
  const navigate = useNavigate()
  const plan = useQuery(getPlan, [])

  return (
    <SettingsLayout title="플랜" description="현재 구독 상태와 사용량을 확인하고 플랜을 변경해요.">
      {plan.loading ? <LoadingBlock label="플랜을 불러오는 중이에요" /> : null}
      {plan.error ? <ErrorBlock message={plan.error} onRetry={plan.reload} /> : null}

      {plan.data ? (
        <div className="max-w-[1048px]">
          <CurrentPlan plan={plan.data} onChange={() => navigate('/credit')} />

          <div className="mt-[34px] flex items-stretch gap-[20px]">
            <SettingsCard className="w-[310px] shrink-0 px-[30px] pt-[28px] pb-[30px]">
              <h3 className="text-[16px] font-bold text-heading">
                {plan.data.current.name} 포함 기능
              </h3>
              <ul className="mt-[26px] flex flex-col gap-[24px]">
                {plan.data.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-[13px]">
                    <img src={checkMarkBlue} alt="" className="size-[13px]" />
                    <span className="text-[14px] text-body">{feature}</span>
                  </li>
                ))}
              </ul>
            </SettingsCard>

            <SettingsCard className="min-w-0 flex-1 px-[30px] pt-[28px] pb-[30px]">
              <span className="inline-flex h-[30px] items-center rounded-full bg-brand-soft px-[14px] text-[13px] font-semibold text-main">
                {plan.data.upgrade.badge}
              </span>
              <h3 className="mt-[22px] text-[20px] font-bold text-heading">
                {plan.data.upgrade.title}
              </h3>
              <p className="mt-[19px] max-w-[620px] text-[14px] leading-[1.6] text-muted">
                {plan.data.upgrade.body}
              </p>
              <button
                type="button"
                onClick={() => navigate('/credit')}
                className="mt-[60px] h-[50px] w-[210px] rounded-[10px] bg-main text-[16px] font-semibold text-white transition-colors hover:bg-[#2872dd]"
              >
                {plan.data.upgrade.cta}
              </button>
              <p className="mt-[16px] text-[13px] text-muted">{plan.data.upgrade.note}</p>
            </SettingsCard>
          </div>
        </div>
      ) : null}
    </SettingsLayout>
  )
}

function CurrentPlan({
  plan,
  onChange,
}: {
  plan: { current: { name: string; price_label: string; next_billing_at: string; used: number; quota: number } }
  onChange: () => void
}) {
  const { name, price_label, next_billing_at, used, quota } = plan.current
  // 분모가 0이면 나눗셈이 NaN 이 되어 막대 너비가 사라진다.
  const percent = quota > 0 ? Math.round((100 * used) / quota) : 0

  return (
    <SettingsCard className="px-[32px] pt-[30px] pb-[30px]">
      <div className="flex items-start justify-between">
        <div>
          <span className="inline-flex h-[30px] items-center rounded-full bg-brand-soft px-[14px] text-[13px] font-semibold text-main">
            현재 플랜
          </span>
          <p className="mt-[18px] text-[24px] font-bold text-heading">{name}</p>
          <p className="mt-[11px] text-[15px] text-body">{price_label}</p>
          <p className="mt-[24px] text-[13px] text-muted">다음 결제일 · {next_billing_at}</p>
        </div>
        <button
          type="button"
          onClick={onChange}
          className="h-[48px] w-[138px] rounded-[10px] border border-divider bg-white text-[15px] font-semibold text-heading transition-colors hover:bg-black/[0.02]"
        >
          플랜 변경
        </button>
      </div>

      <div className="mt-[33px] h-px bg-divider" />

      <div className="mt-[26px] flex items-center gap-[24px]">
        <span className="w-[80px] shrink-0 text-[13px] font-medium text-heading">이번 달 사용량</span>
        <span className="w-[120px] shrink-0 text-[13px] text-muted tabular-nums">
          {used} / {quota}회 테스트
        </span>
        <span className="h-[10px] min-w-0 flex-1 rounded-full bg-track">
          <span
            className="block h-full rounded-full bg-main"
            style={{ width: `${Math.min(100, percent)}%` }}
          />
        </span>
        <span className="w-[36px] shrink-0 text-right text-[12px] font-medium text-main tabular-nums">
          {percent}%
        </span>
      </div>
    </SettingsCard>
  )
}

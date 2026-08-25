import { useState } from 'react'
import { getCredits, type CreditsPayload } from '../api/client'
import { useQuery } from '../api/hooks'
import { SettingsCard, SettingsLayout } from '../components/SettingsLayout'
import { ErrorBlock, LoadingBlock } from '../components/StateView'

/**
 * 설정 · 크레딧 (Figma 311:21384).
 *
 * 충전·구매는 결제가 붙어야 도는 일이다. 누르면 되는 척하지 않고 그 사실을 말한다.
 */
export function SettingsCreditPage() {
  const credits = useQuery(getCredits, [])
  const [notice, setNotice] = useState<string | null>(null)

  return (
    <SettingsLayout
      title="크레딧"
      description="테스트 실행에 사용되는 크레딧 잔액과 내역을 확인해요."
    >
      {credits.loading ? <LoadingBlock label="크레딧을 불러오는 중이에요" /> : null}
      {credits.error ? <ErrorBlock message={credits.error} onRetry={credits.reload} /> : null}

      {credits.data ? (
        <div className="max-w-[1418px] min-w-0">
          <div className="flex items-stretch gap-[18px]">
            <Balance data={credits.data} onCharge={() => setNotice(PAY_NOTICE)} />
            <SettingsCard className="min-w-0 flex-1 px-[28px] pt-[26px] pb-[28px]">
              <h3 className="text-[16px] font-bold text-heading">사용 기준</h3>
              <dl className="mt-[28px] flex flex-col gap-[27px]">
                {credits.data.rules.map((rule) => (
                  <div key={rule.label} className="flex items-center">
                    <dt className="w-[130px] shrink-0 text-[13px] font-medium text-heading">
                      {rule.label}
                    </dt>
                    <dd
                      className={`text-[14px] ${rule.highlight ? 'font-semibold text-main' : 'text-body'}`}
                    >
                      {rule.value}
                    </dd>
                  </div>
                ))}
              </dl>
            </SettingsCard>
          </div>

          <div className="mt-[52px] flex items-start gap-[40px]">
            <div className="min-w-0 flex-1">
              <h2 className="text-[19px] font-bold text-heading">크레딧 충전</h2>
              <p className="mt-[10px] text-[13px] text-muted">필요한 만큼 추가로 구매할 수 있어요.</p>

              {/* 세 칸을 늘 한 줄에 둔다. 고정 폭으로 두면 사이드바 두 개(전역 248 +
                  설정 286)에 밀려 한 칸씩 접히고, 그러면 값 비교가 안 된다. */}
              <div className="mt-[16px] grid grid-cols-3 gap-[14px]">
                {credits.data.packs.map((pack) => (
                  <SettingsCard
                    key={pack.credits}
                    className="flex h-[190px] min-w-0 flex-col px-[24px] pt-[22px] pb-[24px]"
                  >
                    <p className="text-[24px] font-bold text-heading tabular-nums">{pack.credits}</p>
                    <p className="mt-[7px] text-[13px] text-muted">credits</p>
                    {/* 금액과 버튼을 나란히 두면 카드가 좁아졌을 때 서로 겹친다
                        (사이드바가 둘이라 이 화면은 늘 좁다). 금액을 한 줄 위로 올린다. */}
                    <span className="mt-auto text-[16px] font-bold text-heading">{pack.price}</span>
                    <button
                      type="button"
                      onClick={() => setNotice(PAY_NOTICE)}
                      className={`mt-[12px] h-[42px] shrink-0 rounded-[10px] text-[14px] font-semibold transition-colors ${
                        pack.featured
                          ? 'bg-main text-white hover:bg-[#2872dd]'
                          : 'border border-divider bg-white text-heading hover:bg-black/[0.02]'
                      }`}
                    >
                      구매하기
                    </button>
                  </SettingsCard>
                ))}
              </div>

              {notice ? <p className="mt-[16px] text-[13px] text-muted">{notice}</p> : null}
            </div>

            <SettingsCard className="w-[375px] shrink-0 px-[24px] pt-[24px] pb-[26px]">
              <h3 className="text-[16px] font-bold text-heading">최근 사용 내역</h3>
              <ul className="mt-[24px] flex flex-col">
                {credits.data.history.map((row, index) => (
                  <li
                    key={`${row.at}-${row.label}`}
                    className={`flex items-center justify-between py-[16px] ${
                      index > 0 ? 'border-t border-divider' : ''
                    }`}
                  >
                    <div>
                      <p className="text-[11px] text-placeholder">{row.at}</p>
                      <p className="mt-[6px] text-[13px] font-medium text-heading">{row.label}</p>
                    </div>
                    {/* 부호를 색으로도 말한다. 숫자만으로는 충전과 차감이 한눈에 안 갈린다. */}
                    <span
                      className={`text-[14px] font-semibold tabular-nums ${
                        row.delta >= 0 ? 'text-ok' : 'text-heading'
                      }`}
                    >
                      {row.delta >= 0 ? `+${row.delta}` : row.delta}
                    </span>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => setNotice('전체 내역은 준비 중이에요.')}
                className="mt-[20px] text-[13px] font-medium text-main hover:underline"
              >
                전체 내역 보기 →
              </button>
            </SettingsCard>
          </div>
        </div>
      ) : null}
    </SettingsLayout>
  )
}

const PAY_NOTICE = '결제는 아직 붙지 않았어요. 지금은 잔액과 사용 기준만 확인할 수 있어요.'

function Balance({ data, onCharge }: { data: CreditsPayload; onCharge: () => void }) {
  return (
    <div className="flex h-[260px] w-[560px] shrink-0 flex-col rounded-[16px] bg-main px-[32px] pt-[30px] pb-[32px]">
      <p className="text-[14px] font-medium text-white/85">사용 가능한 크레딧</p>
      <p className="mt-[24px] flex items-end gap-[14px]">
        <span className="text-[52px] leading-none font-bold text-white tabular-nums">
          {data.balance}
        </span>
        <span className="pb-[6px] text-[16px] font-medium text-white/85">credits</span>
      </p>
      <div className="mt-auto flex items-end justify-between">
        <span className="text-[13px] text-white/85">
          이번 달 {data.used_this_month} 크레딧 사용
        </span>
        <button
          type="button"
          onClick={onCharge}
          className="h-[48px] w-[190px] rounded-[10px] bg-white text-[15px] font-semibold text-heading transition-opacity hover:opacity-90"
        >
          크레딧 충전
        </button>
      </div>
    </div>
  )
}

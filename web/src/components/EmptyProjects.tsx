import plusIcon from '../assets/icons/plus.svg'

/**
 * 프로젝트가 하나도 없을 때 (Figma 184:362).
 * 카드 그리드 자리를 통째로 대체하는 점선 박스 하나 — 다음 행동이 하나뿐이라 그렇게 그린다.
 */
export function EmptyProjects({ onCreate }: { onCreate: () => void }) {
  return (
    <button
      type="button"
      onClick={onCreate}
      className="flex h-[656px] w-full items-center justify-center gap-[6px] rounded-[22px] border-2 border-dashed border-main bg-main/10 transition-colors hover:bg-main/15"
    >
      <img src={plusIcon} alt="" aria-hidden className="size-[41px]" />
      <span className="text-[24px] leading-[1.45] font-bold text-[#8b8b8b]">새 프로젝트 만들기</span>
    </button>
  )
}

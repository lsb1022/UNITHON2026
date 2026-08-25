import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost'
type Size = 'lg' | 'md'

const VARIANT: Record<Variant, string> = {
  primary: 'bg-main text-white hover:bg-[#2872dd] disabled:bg-[#c4d9f9]',
  secondary: 'bg-white text-ink border border-line hover:bg-black/[0.03]',
  ghost: 'bg-[#f1f2f4] text-subtext hover:bg-[#e8eaed]',
}

const SIZE: Record<Size, string> = {
  lg: 'h-[60px] rounded-[14px] px-[24px] text-[20px] font-bold',
  md: 'h-[48px] rounded-[12px] px-[20px] text-[16px] font-semibold',
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  size?: Size
}

export function Button({
  variant = 'primary',
  size = 'lg',
  className = '',
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-[8px] leading-[1.45] whitespace-nowrap transition-colors disabled:cursor-not-allowed ${VARIANT[variant]} ${SIZE[size]} ${className}`}
      {...rest}
    />
  )
}

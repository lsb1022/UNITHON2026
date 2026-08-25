import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'
import { useId } from 'react'

export function FieldLabel({
  children,
  required,
  hint,
  htmlFor,
}: {
  children: ReactNode
  required?: boolean
  hint?: string
  htmlFor?: string
}) {
  return (
    <label htmlFor={htmlFor} className="flex items-center gap-[6px]">
      <span className="text-[20px] leading-[1.45] font-bold text-heading">{children}</span>
      {required ? <span className="text-[16px] font-bold text-required">*</span> : null}
      {hint ? <span className="text-[14px] text-subtext">{hint}</span> : null}
    </label>
  )
}

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string
  required?: boolean
  hint?: string
  description?: string
  /** 입력창 왼쪽 아이콘/접두어 */
  leading?: ReactNode
  /** 입력창 오른쪽에 붙는 버튼 등 */
  trailing?: ReactNode
  maxLength?: number
  /** 글자수 카운터 노출 여부 */
  counter?: boolean
}

export function TextField({
  label,
  required,
  hint,
  description,
  leading,
  trailing,
  counter,
  maxLength,
  className = '',
  value,
  ...rest
}: TextFieldProps) {
  const id = useId()
  const length = typeof value === 'string' ? value.length : 0

  return (
    <div className="flex flex-col gap-[7px]">
      {label ? (
        <FieldLabel htmlFor={id} required={required} hint={hint}>
          {label}
        </FieldLabel>
      ) : null}
      {description ? <p className="text-[16px] leading-[1.45] text-body">{description}</p> : null}

      <div className="flex items-center gap-[20px]">
        <div className="relative flex h-[62px] w-full max-w-[1100px] items-center gap-[9px] rounded-[16px] border border-line bg-white px-[17px] focus-within:border-main">
          {leading}
          <input
            id={id}
            value={value}
            maxLength={maxLength}
            className={`h-full min-w-0 flex-1 bg-transparent text-[15px] leading-[1.45] outline-none placeholder:text-placeholder ${className}`}
            {...rest}
          />
          {counter && maxLength ? (
            <span className="shrink-0 text-[12px] text-subtext">
              {length} / {maxLength}
            </span>
          ) : null}
        </div>
        {trailing}
      </div>
    </div>
  )
}

type TextAreaFieldProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string
  required?: boolean
  counter?: boolean
}

export function TextAreaField({
  label,
  required,
  counter,
  maxLength,
  value,
  className = '',
  ...rest
}: TextAreaFieldProps) {
  const id = useId()
  const length = typeof value === 'string' ? value.length : 0

  return (
    <div className="flex flex-col gap-[9px]">
      {label ? (
        <FieldLabel htmlFor={id} required={required}>
          {label}
        </FieldLabel>
      ) : null}
      <div className="relative rounded-[16px] border border-line bg-white focus-within:border-main">
        <textarea
          id={id}
          value={value}
          maxLength={maxLength}
          className={`w-full resize-none bg-transparent px-[20px] py-[18px] text-[15px] leading-[1.6] outline-none placeholder:text-placeholder ${className}`}
          {...rest}
        />
        {counter && maxLength ? (
          <span className="absolute right-[20px] bottom-[14px] text-[12px] text-subtext">
            {length} / {maxLength}
          </span>
        ) : null}
      </div>
    </div>
  )
}

"use client";

import { Upload } from "lucide-react";
import { useRef, useState } from "react";

interface Props {
  accept: string;
  multiple?: boolean;
  hint: string;
  disabled?: boolean;
  onFiles: (files: File[]) => void;
}

export function FileDrop({ accept, multiple = false, hint, disabled, onFiles }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (disabled) return;
        const files = Array.from(e.dataTransfer.files);
        if (files.length) onFiles(multiple ? files : [files[0]]);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-[16px] border border-dashed px-4 py-7 text-center transition-all ${
        dragging
          ? "border-primary bg-[#eff4ff] shadow-[inset_0_0_0_3px_rgba(37,99,235,0.08)]"
          : "border-border bg-[#fafbff] hover:border-primary/60 hover:bg-[#f5f8ff]"
      } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-[12px] bg-primary-soft text-primary transition-colors">
        <Upload size={20} />
      </div>
      <p className="text-sm font-medium text-text">点击或拖拽上传</p>
      <p className="text-xs text-muted">{hint}</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) onFiles(multiple ? files : [files[0]]);
          e.target.value = "";
        }}
      />
    </div>
  );
}

import React, { useId, useRef, useState } from 'react';
import { UploadCloud, FileText, X } from 'lucide-react';
import IconButton from './IconButton';
import { cn } from '../../lib/cn';

/**
 * Drag-and-drop file picker.
 *
 * The native input is `sr-only`, NOT `hidden`. `display:none` removes an element
 * from the tab order, which meant the file picker could not be reached or
 * activated by keyboard at all — the worst accessibility defect in the app.
 * `sr-only` keeps it focusable while visually clipped, and the visible label
 * gets a focus ring via `focus-within` so keyboard users can see where they are.
 */
export const FileDropzone = ({ accept, onFileSelected, file, onClear, hint, error }) => {
  const inputId = useId();
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files) => {
    const next = files?.[0];
    if (next) onFileSelected?.(next);
  };

  return (
    <div className="space-y-2">
      <div
        onDragEnter={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer?.files);
        }}
        className={cn(
          'rounded-xl border-2 border-dashed p-8 text-center transition-colors',
          'focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-focus',
          dragging ? 'border-brand-solid bg-brand-subtle/60' : 'border-line-strong bg-surface-3/60',
          error && 'border-danger-fg'
        )}
      >
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={accept}
          className="sr-only"
          aria-describedby={hint ? `${inputId}-hint` : undefined}
          onChange={(e) => handleFiles(e.target.files)}
        />

        {file ? (
          <div className="flex items-center justify-center gap-3">
            <FileText className="w-5 h-5 text-brand-fg shrink-0" aria-hidden="true" />
            <span className="text-sm font-semibold text-fg break-all min-w-0">{file.name}</span>
            {onClear ? (
              <IconButton
                icon={X}
                label="Remove selected file"
                size="sm"
                onClick={() => {
                  if (inputRef.current) inputRef.current.value = '';
                  onClear();
                }}
              />
            ) : null}
          </div>
        ) : (
          <>
            <UploadCloud className="w-8 h-8 text-fg-muted mx-auto mb-3" aria-hidden="true" />
            <label
              htmlFor={inputId}
              className="text-sm font-semibold text-brand-fg cursor-pointer hover:underline"
            >
              Choose a file
            </label>
            <p className="text-sm text-fg-muted mt-1">or drag and drop it here</p>
          </>
        )}
      </div>

      {hint ? (
        <p id={`${inputId}-hint`} className="text-xs text-fg-muted text-center">
          {hint}
        </p>
      ) : null}
    </div>
  );
};

export default FileDropzone;

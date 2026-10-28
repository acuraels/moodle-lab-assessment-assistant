import type { KeyboardEvent } from "react";

// Only validate the selected format. The prototype never reads file contents.
export function isSupportedFile(file: Pick<File, "name">, allowText = false) {
  return (allowText ? /\.(pdf|docx|txt)$/i : /\.(pdf|docx)$/i).test(file.name);
}

export function openFilePicker(event: KeyboardEvent<HTMLLabelElement>) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  event.currentTarget
    .querySelector<HTMLInputElement>('input[type="file"]:not(:disabled)')
    ?.click();
}

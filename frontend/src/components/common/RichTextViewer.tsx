import './RichTextViewer.css';

interface RichTextViewerProps {
  content: string;
  className?: string;
}

export default function RichTextViewer({ content, className }: RichTextViewerProps) {
  if (!content) return null;

  return (
    <div
      className={`rtv ${className || ''}`}
      dangerouslySetInnerHTML={{ __html: content }}
    />
  );
}

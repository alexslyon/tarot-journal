import CorrespondencesViewer from './sections/CorrespondencesViewer';
import './ReferenceTab.css';

interface ReferenceTabProps {
  onNavigateToSettings?: (section: string) => void;
}

export default function ReferenceTab({ onNavigateToSettings }: ReferenceTabProps) {
  return (
    <div className="reference-layout">
      <nav className="reference-layout__sidebar">
        <button className="reference-layout__nav-item reference-layout__nav-item--active">
          Correspondences
        </button>
      </nav>
      <div className="reference-layout__content">
        <CorrespondencesViewer onEditCorrespondences={onNavigateToSettings} />
      </div>
    </div>
  );
}

import { Navigate, Route, Routes } from 'react-router-dom'
import { ComparePage } from './pages/ComparePage'
import { MissionPage } from './pages/MissionPage'
import { NewProjectPage } from './pages/NewProjectPage'
import { NewTestPage } from './pages/NewTestPage'
import { PersonaPage } from './pages/PersonaPage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ReviewPage } from './pages/ReviewPage'
import { RunningPage } from './pages/RunningPage'
import { TestDetailPage } from './pages/TestDetailPage'
import { SidebarProvider } from './state/SidebarContext'
import { WizardProvider } from './state/WizardContext'

export default function App() {
  return (
    <SidebarProvider>
      <WizardProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectsPage />} />
          {/* 두 사이트를 견주는 곳. 프로젝트 안에서는 주소 하나의 결과만 본다. */}
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/projects/new" element={<NewProjectPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/projects/:projectId/tests/new" element={<NewTestPage />} />
          {/* 'new' 가 먼저 걸려야 마법사 첫 화면이 테스트 상세로 새지 않는다. */}
          <Route path="/projects/:projectId/tests/:testId" element={<TestDetailPage />} />
          <Route path="/projects/:projectId/tests/new/mission" element={<MissionPage />} />
          <Route path="/projects/:projectId/tests/new/persona" element={<PersonaPage />} />
          <Route path="/projects/:projectId/tests/new/review" element={<ReviewPage />} />
          <Route path="/projects/:projectId/tests/new/running" element={<RunningPage />} />
          <Route path="*" element={<Navigate to="/projects" replace />} />
        </Routes>
      </WizardProvider>
    </SidebarProvider>
  )
}

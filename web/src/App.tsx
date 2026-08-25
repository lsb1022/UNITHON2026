import { Navigate, Route, Routes } from 'react-router-dom'
import { MissionPage } from './pages/MissionPage'
import { NewProjectPage } from './pages/NewProjectPage'
import { NewTestPage } from './pages/NewTestPage'
import { PersonaPage } from './pages/PersonaPage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ReviewPage } from './pages/ReviewPage'
import { RunningPage } from './pages/RunningPage'
import { SidebarProvider } from './state/SidebarContext'
import { WizardProvider } from './state/WizardContext'

export default function App() {
  return (
    <SidebarProvider>
      <WizardProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/new" element={<NewProjectPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/projects/:projectId/tests/new" element={<NewTestPage />} />
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

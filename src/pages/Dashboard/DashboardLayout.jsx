import Sidebar from '../../components/Sidebar/Sidebar';
import Navbar from '../../components/Navbar/Navbar';
import FAB from '../../components/FAB/FAB';
import { Outlet } from 'react-router-dom';

export default function DashboardLayout() {
  return (
    <div className="font-sans bg-gradient-to-br from-neutral-50 to-primary-50/20 min-h-screen flex">
      <Sidebar />
      <div className="flex-1" style={{ marginLeft: '280px' }}>
        <Navbar />
        <main className="relative">
          <Outlet />
        </main>
        <FAB />
      </div>
    </div>
  );
}

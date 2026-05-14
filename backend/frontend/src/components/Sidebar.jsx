import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  Settings,
  PieChart,
  Search,
  Layers,
  Lightbulb,
  Image,
} from 'lucide-react';

const Sidebar = () => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Upload Data', path: '/upload', icon: UploadCloud },
    { name: 'Analytics', path: '/analytics', icon: PieChart },
    { name: 'Clusters', path: '/clusters', icon: Layers },
    { name: 'Feedback explorer', path: '/explorer', icon: Search },
    { name: 'Insights', path: '/insights', icon: Lightbulb },
    { name: 'Visualizations', path: '/visualizations', icon: Image },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-800 h-[calc(100vh-4rem)] flex-shrink-0">
      <div className="p-4">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Main Menu
        </div>
        <ul className="space-y-2">
          {navItems.map((item) => (
            <li key={item.name}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-600/10 text-blue-500 font-medium'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                  }`
                }
              >
                <item.icon size={20} />
                <span>{item.name}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
};

export default Sidebar;

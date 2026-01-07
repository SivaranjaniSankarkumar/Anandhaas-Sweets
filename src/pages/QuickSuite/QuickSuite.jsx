import sweetsBg from '../../assets/images/sweets-bg.webp';
import { ExternalLink } from 'lucide-react';

export default function QuickSuite() {
  const handleOpenDashboard = () => {
    window.open('https://us-east-1.quicksight.aws.amazon.com/sn/accounts/522505216519/dashboards/ce3e9dca-a2db-43f2-9b46-ae1394a22a49?directory_alias=anandhaas-sweets', '_blank');
  };

  return (
    <div className="h-full w-full relative">
      <div 
        className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0"
        style={{ backgroundImage: `url(${sweetsBg})` }}
      />
      <div className="relative z-10 h-full w-full flex items-center justify-center pt-64">
        <div className="text-center">
          <button
            onClick={handleOpenDashboard}
            className="flex items-center gap-3 bg-primary-600 hover:bg-primary-700 text-white font-medium py-4 px-8 rounded-xl transition-colors shadow-lg"
          >
            <ExternalLink className="w-5 h-5" />
            Open QuickSight Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
import Dashboard from './pages/Dashboard';
import PnLReport from './pages/PnLReport';
import OrdersReport from './pages/OrdersReport';
import SignalsReport from './pages/SignalsReport';
import AlertsReport from './pages/AlertsReport';
import QuickSettings from './pages/QuickSettings';
import Account from './pages/Account';

const routes: Record<string, React.FC> = {
  dashboard: Dashboard,
  pnl: PnLReport,
  orders: OrdersReport,
  signals: SignalsReport,
  alerts: AlertsReport,
  settings: QuickSettings,
  account: Account,
};

export default routes;
import { Component } from 'react';
import { AlertTriangle } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[320px] rounded-xl border border-red-500/30 bg-red-500/10 p-6 flex items-center">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="text-red-400" size={20} />
              <h3 className="font-semibold text-red-200">Component rendering error</h3>
            </div>
            <p className="text-sm text-red-300/80">{this.state.error?.message || 'An unexpected error occurred'}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-3 px-3 py-1.5 text-xs font-medium rounded border border-red-400/40 bg-red-500/20 text-red-200 hover:bg-red-500/30 transition"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

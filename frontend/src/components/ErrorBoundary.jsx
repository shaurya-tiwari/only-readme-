import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error("RideShield UI boundary caught an error", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="panel mx-auto my-8 max-w-3xl p-8">
          <p className="eyebrow">Surface recovery</p>
          <h2 className="mt-3 text-3xl font-bold text-on-surface">This screen hit an unexpected error.</h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-on-surface-variant">
            The backend may still be running correctly, but this view needs a refresh to restore the current state.
          </p>
          <button type="button" className="button-primary mt-6" onClick={() => window.location.reload()}>
            Reload page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

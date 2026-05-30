"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: React.ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
}

/** Catches render-time crashes in its subtree and shows a friendly message. */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    // Avoid logging anything sensitive; type/name only.
    console.error("UI ErrorBoundary caught:", error.name);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-red-900/50 bg-red-950/20 p-8 text-center">
          <AlertTriangle className="h-8 w-8 text-red-400" />
          <p className="font-medium text-red-200">
            {this.props.fallbackTitle ?? "Something went wrong rendering this section."}
          </p>
          <Button variant="outline" size="sm" onClick={() => this.setState({ hasError: false })}>
            Try again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}

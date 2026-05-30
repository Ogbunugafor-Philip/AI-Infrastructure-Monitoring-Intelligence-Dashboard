import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const alertVariants = cva(
  "relative w-full rounded-lg border px-4 py-3 text-sm flex items-start gap-2",
  {
    variants: {
      variant: {
        default: "border-slate-700 bg-slate-900/60 text-slate-200",
        success: "border-emerald-700/50 bg-emerald-900/20 text-emerald-300",
        destructive: "border-red-700/50 bg-red-900/20 text-red-300",
        warning: "border-amber-700/50 bg-amber-900/20 text-amber-300",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

function Alert({ className, variant, ...props }: AlertProps) {
  return <div role="alert" className={cn(alertVariants({ variant }), className)} {...props} />;
}

export { Alert, alertVariants };

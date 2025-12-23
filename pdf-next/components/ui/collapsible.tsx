"use client"

import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

const Collapsible = React.forwardRef<
  HTMLDivElement,
  React.ComponentPropsWithoutRef<"div">
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("", className)} {...props} />
))
Collapsible.displayName = "Collapsible"

const CollapsibleTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ComponentPropsWithoutRef<"button"> & {
    isOpen?: boolean
  }
>(({ className, children, isOpen, ...props }, ref) => (
  <button
    ref={ref}
    type="button"
    className={cn(
      "flex w-full items-center justify-between py-3 px-4 text-left font-medium transition-all hover:bg-gray-50 rounded-lg",
      className
    )}
    {...props}
  >
    <div className="flex-1">{children}</div>
    <ChevronDown className={cn("h-4 w-4 shrink-0 transition-transform duration-200 ml-2", isOpen && "rotate-180")} />
  </button>
))
CollapsibleTrigger.displayName = "CollapsibleTrigger"

const CollapsibleContent = React.forwardRef<
  HTMLDivElement,
  React.ComponentPropsWithoutRef<"div"> & {
    isOpen?: boolean
  }
>(({ className, children, isOpen, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "overflow-hidden transition-all duration-300 ease-in-out",
      isOpen ? "max-h-screen opacity-100" : "max-h-0 opacity-0",
      className
    )}
    style={{
      maxHeight: isOpen ? '1000px' : '0px',
    }}
    {...props}
  >
    <div className={cn("pb-4 pt-2", isOpen ? "block" : "hidden")}>{children}</div>
  </div>
))
CollapsibleContent.displayName = "CollapsibleContent"

export { Collapsible, CollapsibleTrigger, CollapsibleContent }
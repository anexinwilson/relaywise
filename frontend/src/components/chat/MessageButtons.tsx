import { Button } from "@/components/ui/button";

interface MessageButtonsProps {
  onOptionClick: (value: string, label: string) => void;
}

export function MessageButtons({ onOptionClick }: MessageButtonsProps) {
  const options = [
    { label: "🔍 Search across apps", value: "search" },
    { label: "⚡ Set up automation", value: "automate" },
    { label: "🔌 Connect more apps", value: "integrations" },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-semibold text-foreground">
          Hi! I&apos;m ready to help you create a new automation.
        </h2>
        <p className="text-muted-foreground">What would you like to automate?</p>
      </div>

      <div className="flex flex-wrap gap-3 justify-center">
        {options.map((option, i) => (
          <Button
            key={i}
            variant="outline"
            size="lg"
            className="h-12 px-6"
            onClick={() => onOptionClick(option.value, option.label)}
          >
            {option.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

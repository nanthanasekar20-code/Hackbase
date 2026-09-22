import EmptyState from "../components/ui/EmptyState.jsx";
import Button from "../components/ui/Button.jsx";

export default function NotFound() {
  return (
    <main className="page">
      <div className="container">
        <EmptyState
          title="Page not found"
          description="That page doesn't exist — head back home."
          action={
            <Button to="/" size="sm">
              Back to Home
            </Button>
          }
        />
      </div>
    </main>
  );
}

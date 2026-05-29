import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Car, Zap, Shield, BarChart3 } from "lucide-react";
import { slotsApi } from "@/api/slots";
import { Button } from "@/components/ui/button";
import type { Stats } from "@/types";

export function LandingPage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    slotsApi.stats().then((r) => setStats(r.data)).catch(() => null);
    const interval = setInterval(() => {
      slotsApi.stats().then((r) => setStats(r.data)).catch(() => null);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const features = [
    {
      icon: Zap,
      title: "Real-Time Detection",
      desc: "Computer vision powered by YOLOv8 tracks every vehicle entry and exit instantly.",
    },
    {
      icon: Car,
      title: "Instant Booking",
      desc: "Reserve your spot before you arrive. Pay online and walk straight in.",
    },
    {
      icon: BarChart3,
      title: "Smart Analytics",
      desc: "Operators see live occupancy, revenue trends, and utilization heatmaps.",
    },
    {
      icon: Shield,
      title: "Secure Payments",
      desc: "Powered by Razorpay test mode — safe, fast, and zero-friction checkout.",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Car className="h-6 w-6 text-primary" />
          <span className="font-bold text-lg">ParkPulse</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login">
            <Button variant="ghost" size="sm">Sign In</Button>
          </Link>
          <Link to="/register">
            <Button size="sm">Get Started</Button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 py-24 text-center">
        <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm text-primary mb-8">
          <Zap className="h-3.5 w-3.5" />
          CV-Powered Smart Parking
        </div>
        <h1 className="text-5xl font-bold text-foreground mb-6 leading-tight">
          Find. Book. <span className="text-primary">Park.</span>
        </h1>
        <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
          Real-time slot availability powered by computer vision. Book your spot,
          pay online, and arrive stress-free.
        </p>

        {/* Live counter */}
        {stats && (
          <div className="inline-flex items-center gap-6 rounded-xl border border-border bg-card px-8 py-4 mb-10">
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">{stats.free}</div>
              <div className="text-xs text-muted-foreground mt-1">Available Now</div>
            </div>
            <div className="w-px h-10 bg-border" />
            <div className="text-center">
              <div className="text-3xl font-bold">{stats.total}</div>
              <div className="text-xs text-muted-foreground mt-1">Total Slots</div>
            </div>
            <div className="w-px h-10 bg-border" />
            <div className="text-center">
              <div className="text-3xl font-bold text-amber-400">
                {(stats.occupancy_rate * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-muted-foreground mt-1">Occupied</div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-center gap-4">
          <Link to="/register">
            <Button size="lg">Book a Slot</Button>
          </Link>
          <Link to="/login">
            <Button variant="outline" size="lg">View Dashboard</Button>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {features.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="rounded-lg border border-border bg-card p-5 hover:border-primary/30 transition-colors"
            >
              <div className="rounded-md bg-primary/10 p-2 w-fit mb-3">
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-semibold text-sm mb-2">{title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

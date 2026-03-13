'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { DashboardSidebar } from '@/components/dashboard/DashboardSidebar';
import { FileText, Briefcase, Calendar, CheckCircle2, Clock, AlertCircle, Loader } from 'lucide-react';
import { doc, getDoc } from 'firebase/firestore';
import { db } from '@/lib/firebase';

interface Application {
  id: number;
  company: string;
  position: string;
  status: string;
  date: string;
  link: string;
}

export default function ApplicationsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobsAppliedCount, setJobsAppliedCount] = useState(0);
  const [dataLoading, setDataLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (!user) return;

    const fetchApplications = async () => {
      try {
        const userRef = doc(db, 'users', user.uid);
        const snap = await getDoc(userRef);
        if (snap.exists()) {
          const data = snap.data();
          setApplications(data.appliedJobs || []);
          setJobsAppliedCount(data.jobsAppliedCount || 0);
        }
      } catch (err) {
        console.error('[Applications] Failed to fetch:', err);
      } finally {
        setDataLoading(false);
      }
    };

    fetchApplications();
  }, [user]);

  if (loading || !user) {
    return null;
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'applied':
        return <CheckCircle2 className="w-5 h-5 text-primary" />;
      case 'in-review':
        return <Clock className="w-5 h-5 text-accent" />;
      case 'rejected':
        return <AlertCircle className="w-5 h-5 text-destructive" />;
      default:
        return null;
    }
  };

  const getStatusLabel = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1).replace('-', ' ');
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader />

      <div className="flex h-[calc(100vh-60px)]">
        <DashboardSidebar />

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto p-6 space-y-8">
            {/* Header */}
            <div>
              <h1 className="text-3xl font-bold mb-2">Your Applications</h1>
              <p className="text-foreground/60">Track all your job applications in one place</p>
            </div>

            {/* Stats */}
            <div className="grid md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-card/50 border border-border/40">
                <p className="text-sm text-foreground/60 mb-1">Total Applications</p>
                <p className="text-3xl font-bold text-primary">{jobsAppliedCount}</p>
              </div>
              <div className="p-4 rounded-lg bg-card/50 border border-border/40">
                <p className="text-sm text-foreground/60 mb-1">In Review</p>
                <p className="text-3xl font-bold text-accent">
                  {applications.filter(a => a.status === 'in-review').length}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-card/50 border border-border/40">
                <p className="text-sm text-foreground/60 mb-1">Applied</p>
                <p className="text-3xl font-bold text-primary">
                  {applications.filter(a => a.status === 'applied').length}
                </p>
              </div>
            </div>

            {/* Applications List */}
            <div className="space-y-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Briefcase className="w-5 h-5" />
                All Applications
              </h2>

              {dataLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader className="w-6 h-6 animate-spin text-primary" />
                </div>
              ) : applications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-foreground/40">
                  <FileText className="w-10 h-10 mb-3" />
                  <p className="text-lg">No applications yet</p>
                  <p className="text-sm mt-1">Use Auto Apply on the dashboard to start applying to jobs.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {applications.map(app => (
                    <div
                      key={app.id}
                      className="p-4 rounded-lg bg-card/50 border border-border/40 hover:border-primary/40 transition"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                              <Briefcase className="w-5 h-5 text-primary" />
                            </div>
                            <div>
                              <h3 className="font-semibold text-lg">{app.position}</h3>
                              <p className="text-sm text-foreground/60">{app.company}</p>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {getStatusIcon(app.status)}
                          <span className="text-sm font-medium">{getStatusLabel(app.status)}</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/40">
                        <div className="flex items-center gap-2 text-sm text-foreground/60">
                          <Calendar className="w-4 h-4" />
                          {new Date(app.date).toLocaleDateString()}
                        </div>
                        {app.link && (
                          <a
                            href={app.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary hover:text-primary/80 transition"
                          >
                            View Job →
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
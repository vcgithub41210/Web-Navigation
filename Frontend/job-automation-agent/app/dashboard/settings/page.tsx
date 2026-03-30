'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { DashboardSidebar } from '@/components/dashboard/DashboardSidebar';
import { Save, Upload, Mail, User, Briefcase, FileText, Trash2, Download } from 'lucide-react';
import { doc, updateDoc } from 'firebase/firestore';
import { db } from '@/lib/firebase';
import { deleteResumeFromSupabase, uploadResumeToSupabase } from '@/lib/supabase';

export default function SettingsPage() {
  const { user, userProfile, loading } = useAuth();
  const router = useRouter();

  const [formData, setFormData] = useState({
    displayName: '',
    email: '',
    jobTitle: '',
    about: '',
    resumeURL: '',
    resumeFileName: ''
  });

  const [saving, setSaving] = useState(false);
  const [uploadingResume, setUploadingResume] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }

    if (userProfile) {
      setFormData({
        displayName: userProfile.displayName || '',
        email: userProfile.email || '',
        jobTitle: userProfile.jobTitle || '',
        about: userProfile.about || '',
        resumeURL: userProfile.resumeURL || '',
        resumeFileName: userProfile.resumeURL ? 'resume.pdf' : ''
      });
    }
  }, [user, loading, router, userProfile]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (!file || !user) return;

  setUploadingResume(true);
  setMessage('');

  try {
    // Best-effort cleanup of old Supabase resume before replacing it.
    if (formData.resumeURL) {
      try {
        await deleteResumeFromSupabase(user.uid);
      } catch (e) {
        // Ignore
      }
    }

    // Upload new resume to Supabase and store its public URL.
    const downloadURL = await uploadResumeToSupabase(file, user.uid);

    await updateDoc(doc(db, 'users', user.uid), {
      resumeURL: downloadURL,
      updatedAt: new Date()
    });

    setFormData(prev => ({
      ...prev,
      resumeURL: downloadURL,
      resumeFileName: 'resume.pdf'
    }));

    setMessage('Resume uploaded successfully!');
  } catch (err: any) {
    setMessage('Failed to upload resume: ' + err.message);
  } finally {
    setUploadingResume(false);
  }
};

const handleDeleteResume = async () => {
  if (!user || !formData.resumeURL) return;

  try {
    setUploadingResume(true);

    // Delete from Supabase storage.
    try {
      await deleteResumeFromSupabase(user.uid);
    } catch (e) {
      // Ignore
    }

    await updateDoc(doc(db, 'users', user.uid), {
      resumeURL: '',
      updatedAt: new Date()
    });

    setFormData(prev => ({
      ...prev,
      resumeURL: '',
      resumeFileName: ''
    }));

    setMessage('Resume deleted successfully!');
  } catch (err: any) {
    setMessage('Failed to delete resume: ' + err.message);
  } finally {
    setUploadingResume(false);
  }
};







  const handleSaveChanges = async () => {
    if (!user) return;

    setSaving(true);
    setMessage('');

    try {
      await updateDoc(doc(db, 'users', user.uid), {
        displayName: formData.displayName,
        jobTitle: formData.jobTitle,
        about: formData.about,
        updatedAt: new Date()
      });

      setMessage('Profile updated successfully!');
    } catch (err: any) {
      setMessage('Failed to update profile: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader />

      <div className="flex h-[calc(100vh-60px)]">
        <DashboardSidebar />

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto p-6 space-y-8">
            {/* Header */}
            <div>
              <h1 className="text-3xl font-bold mb-2">Settings</h1>
              <p className="text-foreground/60">Manage your profile and resume</p>
            </div>

            {/* Message */}
            {message && (
              <div className={`p-4 rounded-lg border ${
                message.includes('successfully')
                  ? 'bg-primary/10 border-primary/30 text-primary'
                  : 'bg-destructive/10 border-destructive/30 text-destructive'
              }`}>
                {message}
              </div>
            )}

            {/* Profile Section */}
            <div className="space-y-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <User className="w-5 h-5 text-primary" />
                Profile Information
              </h2>

              <div className="space-y-4 bg-card/50 border border-border/40 rounded-lg p-6">
                <div>
                  <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                    <User className="w-4 h-4" />
                    Full Name
                  </label>
                  <input
                    type="text"
                    name="displayName"
                    value={formData.displayName}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                    <Mail className="w-4 h-4" />
                    Email
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    disabled
                    className="w-full px-4 py-2 bg-input border border-border/40 rounded-lg opacity-50 cursor-not-allowed"
                  />
                  <p className="text-xs text-foreground/50 mt-1">Email cannot be changed</p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                    <Briefcase className="w-4 h-4" />
                    Job Title
                  </label>
                  <input
                    type="text"
                    name="jobTitle"
                    value={formData.jobTitle}
                    onChange={handleInputChange}
                    placeholder="e.g., Senior Software Engineer"
                    className="w-full px-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">About You</label>
                  <textarea
                    name="about"
                    value={formData.about}
                    onChange={handleInputChange}
                    placeholder="Tell us about yourself..."
                    rows={4}
                    className="w-full px-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition resize-none"
                  />
                </div>

                <button
                  onClick={handleSaveChanges}
                  disabled={saving}
                  className="w-full py-3 px-4 bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  <Save className="w-5 h-5" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>

            {/* Resume Section */}
            <div className="space-y-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <FileText className="w-5 h-5 text-accent" />
                Resume Management
              </h2>

              <div className="space-y-4 bg-card/50 border border-border/40 rounded-lg p-6">
                {formData.resumeURL ? (
                  <div className="flex items-center justify-between p-4 bg-accent/10 border border-accent/30 rounded-lg">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-accent" />
                      <div>
                        <p className="font-medium">{formData.resumeFileName}</p>
                        <p className="text-sm text-foreground/60">Resume uploaded</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <a
                        href={formData.resumeURL}
                        download
                        className="p-2 hover:bg-accent/20 rounded-lg transition"
                        title="Download resume"
                      >
                        <Download className="w-5 h-5 text-accent" />
                      </a>
                      <button
                        onClick={handleDeleteResume}
                        disabled={uploadingResume}
                        className="p-2 hover:bg-destructive/20 rounded-lg transition disabled:opacity-50"
                        title="Delete resume"
                      >
                        <Trash2 className="w-5 h-5 text-destructive" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-foreground/60">No resume uploaded yet</p>
                )}

                <label className="flex items-center justify-center w-full px-4 py-6 border-2 border-dashed border-primary/30 rounded-lg cursor-pointer hover:border-primary/60 transition bg-primary/5">
                  <div className="text-center">
                    <Upload className="w-8 h-8 text-primary mx-auto mb-2" />
                    <p className="font-medium text-sm">
                      {uploadingResume ? 'Uploading...' : 'Click to upload or drag and drop'}
                    </p>
                    <p className="text-xs text-foreground/40">PDF, DOC, DOCX (Max 10MB)</p>
                  </div>
                  <input
                    type="file"
                    onChange={handleResumeUpload}
                    accept=".pdf,.doc,.docx"
                    disabled={uploadingResume}
                    className="hidden"
                  />
                </label>

                <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg text-sm text-foreground/70">
                  💡 Your resume will be used to automatically fill out job applications. Keep it up to date!
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

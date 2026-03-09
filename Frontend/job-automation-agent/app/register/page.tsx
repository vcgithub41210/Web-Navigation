'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { createUserWithEmailAndPassword, signInWithPopup, GoogleAuthProvider, updateProfile, getRedirectResult, signInWithRedirect } from 'firebase/auth';
import { auth, db, storage } from '@/lib/firebase';
import { doc, setDoc } from 'firebase/firestore';
import { uploadResumeToSupabase } from '@/lib/supabase';
import { Mail, Lock, User, Upload, Loader, Chrome, FileUp } from 'lucide-react';

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    jobTitle: '',
    about: ''
  });
  const [resume, setResume] = useState<File | null>(null);
  const [resumePreview, setResumePreview] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState<'form' | 'questionnaire'>('form');
  const { user } = useAuth();
  const router = useRouter();

   
  const handleResumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setResume(file);
      // Create preview name
      setResumePreview(file.name);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleEmailRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Validate
      if (formData.password !== formData.confirmPassword) {
        setError('Passwords do not match');
        setLoading(false);
        return;
      }

      // Create user
      const userCredential = await createUserWithEmailAndPassword(auth, formData.email, formData.password);
      const newUser = userCredential.user;

      // Update profile
      await updateProfile(newUser, {
        displayName: formData.fullName
      });

      // Upload resume to SUPABASE if provided
      let resumeURL = '';
      if (resume) {
        try {
          // Upload to Supabase at: resume_bucket/{firebase_uid}/resume.pdf
          resumeURL = await uploadResumeToSupabase(resume, newUser.uid);
        } catch (uploadErr: any) {
          console.error('Resume upload failed:', uploadErr);
          setError('Account created but resume upload failed. Please upload in settings.');
          // Continue anyway - user can upload later in settings
        }
      }

      // Create user profile in Firestore
      await setDoc(doc(db, 'users', newUser.uid), {
        uid: newUser.uid,
        email: formData.email,
        displayName: formData.fullName,
        jobTitle: formData.jobTitle,
        about: formData.about,
        resumeURL: resumeURL, // Now contains Supabase URL
        createdAt: new Date(),
        updatedAt: new Date()
      });

      setStep('questionnaire');
    } catch (err: any) {
      setError(err.message || 'Failed to register');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleRegister = async () => {
  setError('');
  setLoading(true);

  try {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    const newUser = result.user;

    // Store user in Firestore
    await setDoc(doc(db, 'users', newUser.uid), {
      uid: newUser.uid,
      email: newUser.email,
      displayName: newUser.displayName || '',
      photoURL: newUser.photoURL || '',
      jobTitle: '',
      about: '',
      resumeURL: '',
      provider: 'google',
      createdAt: new Date(),
      updatedAt: new Date()
    }, { merge: true });

    router.push('/dashboard');
  } catch (err: any) {
    let errorMessage = err.message || 'Failed to register with Google';

    if (err.code === 'auth/popup-closed-by-user') {
      errorMessage = 'Popup closed before completing sign in';
    }
 

    if (err.code === 'auth/unauthorized-domain') {
      errorMessage = 'Domain not authorized in Firebase';
    }

    setError(errorMessage);
    console.log('Google auth error:', err.code);
  } finally {
    setLoading(false);
  }
};
 

  const handleQuestionnaireSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    router.push('/dashboard');
  };

  if (user) {
    return null;
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-20 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary/20 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-10 w-72 h-72 bg-accent/20 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-2xl slide-in-up">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center mx-auto mb-4">
            <span className="text-white font-bold text-2xl">JA</span>
          </div>
          <h1 className="text-3xl font-bold mb-2">
            {step === 'form' ? 'Create Your Account' : 'Tell Us About Yourself'}
          </h1>
          <p className="text-foreground/60">
            {step === 'form' ? 'Join JobAgent and start automating your applications' : 'Help us personalize your job search experience'}
          </p>
        </div>

        <div className="bg-card/50 border border-border/40 rounded-2xl p-8 backdrop-blur-sm">
          {step === 'form' ? (
            <>
              {/* Google Sign Up */}
              <button
                onClick={handleGoogleRegister}
                disabled={loading}
                className="w-full py-3 px-4 border border-border/60 rounded-lg font-medium hover:bg-card/80 transition flex items-center justify-center gap-2 mb-6 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Chrome className="w-5 h-5" />
                {loading ? 'Creating account...' : 'Sign up with Google'}
              </button>

              <div className="relative mb-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border/40" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-card/50 text-foreground/60">Or with email</span>
                </div>
              </div>

              {/* Error message */}
              {error && (
                <div className="mb-4 p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-destructive text-sm">
                  {error}
                </div>
              )}

              {/* Registration form */}
              <form onSubmit={handleEmailRegister} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Full Name</label>
                  <div className="relative">
                    <User className="absolute left-3 top-3 w-5 h-5 text-foreground/40" />
                    <input
                      type="text"
                      name="fullName"
                      value={formData.fullName}
                      onChange={handleInputChange}
                      placeholder="John Doe"
                      required
                      className="w-full pl-10 pr-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 w-5 h-5 text-foreground/40" />
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      placeholder="you@example.com"
                      required
                      className="w-full pl-10 pr-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
                    />
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 w-5 h-5 text-foreground/40" />
                      <input
                        type="password"
                        name="password"
                        value={formData.password}
                        onChange={handleInputChange}
                        placeholder="••••••••"
                        required
                        className="w-full pl-10 pr-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Confirm Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 w-5 h-5 text-foreground/40" />
                      <input
                        type="password"
                        name="confirmPassword"
                        value={formData.confirmPassword}
                        onChange={handleInputChange}
                        placeholder="••••••••"
                        required
                        className="w-full pl-10 pr-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Current Job Title</label>
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
                  <label className="block text-sm font-medium mb-2">About You (Optional)</label>
                  <textarea
                    name="about"
                    value={formData.about}
                    onChange={handleInputChange}
                    placeholder="Tell us about yourself..."
                    rows={3}
                    className="w-full px-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition resize-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                    <Upload className="w-4 h-4" />
                    Upload Your Resume (Optional)
                  </label>
                  <label className="flex items-center justify-center w-full px-4 py-6 border-2 border-dashed border-primary/30 rounded-lg cursor-pointer hover:border-primary/60 transition bg-primary/5">
                    <div className="text-center">
                      {resumePreview ? (
                        <>
                          <FileUp className="w-8 h-8 text-accent mx-auto mb-2" />
                          <p className="font-medium text-sm">{resumePreview}</p>
                        </>
                      ) : (
                        <>
                          <Upload className="w-8 h-8 text-foreground/40 mx-auto mb-2" />
                          <p className="font-medium text-sm">Click to upload or drag and drop</p>
                          <p className="text-xs text-foreground/40">PDF, DOC, DOCX (Max 10MB)</p>
                        </>
                      )}
                    </div>
                    <input
                      type="file"
                      onChange={handleResumeChange}
                      accept=".pdf,.doc,.docx"
                      className="hidden"
                    />
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 px-4 bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader className="w-5 h-5 animate-spin" />
                      Creating account...
                    </>
                  ) : (
                    'Create Account & Continue'
                  )}
                </button>
              </form>
            </>
          ) : (
            <form onSubmit={handleQuestionnaireSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-4">What types of positions are you interested in?</label>
                <div className="space-y-2">
                  {['Full-time', 'Contract', 'Freelance', 'Part-time', 'Internship'].map((type) => (
                    <label key={type} className="flex items-center gap-3 p-3 rounded-lg border border-border/40 hover:border-primary/40 cursor-pointer transition">
                      <input type="checkbox" defaultChecked className="w-4 h-4 accent-primary" />
                      <span>{type}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-4">Preferred industries?</label>
                <input
                  type="text"
                  placeholder="e.g., Tech, Finance, Healthcare"
                  className="w-full px-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-4">Salary expectations?</label>
                <input
                  type="text"
                  placeholder="e.g., $100,000 - $150,000"
                  className="w-full px-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
                />
              </div>

              <button
                type="submit"
                className="w-full py-3 px-4 bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 transition"
              >
                Start Using JobAgent
              </button>
            </form>
          )}
        </div>

        {/* Sign in link */}
        <p className="text-center mt-6 text-foreground/60">
          Already have an account?{' '}
          <Link href="/login" className="text-primary hover:text-primary/80 font-medium">
            Sign in
          </Link>
        </p>

        {/* Back to home */}
        <div className="text-center mt-4">
          <Link href="/" className="text-foreground/60 hover:text-foreground text-sm transition">
            ← Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
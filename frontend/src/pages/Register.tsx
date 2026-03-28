import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '@/services/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }
    setLoading(true);
    try {
      await authService.register({ email, username, full_name: fullName, password });
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <Card className="w-96 bg-surface border-white/10">
        <CardHeader>
          <CardTitle className="text-white text-center">Register</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="email" className="text-slate-300">Email *</Label>
              <Input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)}
                required className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="username" className="text-slate-300">Username *</Label>
              <Input id="username" value={username} onChange={e => setUsername(e.target.value)}
                required minLength={3} className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="fullName" className="text-slate-300">Full Name</Label>
              <Input id="fullName" value={fullName} onChange={e => setFullName(e.target.value)}
                className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="password" className="text-slate-300">Password *</Label>
              <Input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)}
                required className="bg-background border-white/10 text-white" />
            </div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <Button type="submit" disabled={loading} className="w-full bg-primary hover:bg-primary/90">
              {loading ? 'Registering...' : 'Register'}
            </Button>
            <p className="text-center text-sm text-slate-400">
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:underline">Login</Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default Register;

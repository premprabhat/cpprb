import unittest

import numpy as np

from cpprb import ReplayBuffer as nowReplayBuffer
from cpprb.experimental import ReplayBuffer,PrioritizedReplayBuffer
from cpprb.experimental import create_buffer

class TestExperimentalReplayBuffer(unittest.TestCase):
    def test_buffer(self):

        buffer_size = 256
        obs_shape = (15,15)
        act_dim = 5

        N = 512

        rb = nowReplayBuffer(buffer_size,obs_shape=obs_shape,act_dim=act_dim)
        erb = ReplayBuffer(buffer_size,{"obs":{"shape": obs_shape},
                                        "act":{"shape": act_dim},
                                        "rew":{},
                                        "next_obs":{"shape": obs_shape},
                                        "done":{}})

        for i in range(N):
            obs = np.full(obs_shape,i,dtype=np.double)
            act = np.full(act_dim,i,dtype=np.double)
            rew = i
            next_obs = obs + 1
            done = 0

            rb.add(obs,act,rew,next_obs,done)
            erb.add(obs=obs,act=act,rew=rew,next_obs=next_obs,done=done)

        s = rb._encode_sample(range(buffer_size))
        es = erb._encode_sample(range(buffer_size))

        np.testing.assert_allclose(s["obs"],es["obs"])
        np.testing.assert_allclose(s["act"],es["act"])
        np.testing.assert_allclose(s["rew"],es["rew"])
        np.testing.assert_allclose(s["next_obs"],es["next_obs"])
        np.testing.assert_allclose(s["done"],es["done"])

        erb.sample(32)

        erb.clear()

        self.assertEqual(erb.get_next_index(),0)
        self.assertEqual(erb.get_stored_size(),0)

    def test_add(self):
        buffer_size = 256
        obs_shape = (15,15)
        act_dim = 5

        rb = ReplayBuffer(buffer_size,{"obs":{"shape": obs_shape},
                                       "act":{"shape": act_dim},
                                       "rew":{},
                                       "next_obs": {"shape": obs_shape},
                                       "done": {}})

        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

        obs = np.zeros(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        next_obs = obs + 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,next_obs=next_obs,done=done)

        self.assertEqual(rb.get_next_index(),1)
        self.assertEqual(rb.get_stored_size(),1)

        with self.assertRaises(KeyError):
            rb.add(obs=obs)

        self.assertEqual(rb.get_next_index(),1)
        self.assertEqual(rb.get_stored_size(),1)

        obs = np.stack((obs,obs))
        act = np.stack((act,act))
        rew = (1,0)
        next_obs = np.stack((next_obs,next_obs))
        done = (0.0,1.0)

        rb.add(obs=obs,act=act,rew=rew,next_obs=next_obs,done=done)

        self.assertEqual(rb.get_next_index(),3)
        self.assertEqual(rb.get_stored_size(),3)


    def test_next_obs(self):
        buffer_size = 256
        obs_shape = (15,15)
        act_dim = 5

        rb = ReplayBuffer(buffer_size,{"obs":{"shape": obs_shape,"dtype": np.ubyte},
                                       "act":{"shape": act_dim},
                                       "rew":{},
                                       "done": {}},
                          next_of = "obs")

        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

        obs = np.zeros(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done)

        self.assertEqual(rb.get_next_index(),1)
        self.assertEqual(rb.get_stored_size(),1)

        with self.assertRaises(KeyError):
            rb.add(obs=obs)

        self.assertEqual(rb.get_next_index(),1)
        self.assertEqual(rb.get_stored_size(),1)

        next_obs = rb.sample(32)["next_obs"]


        for i in range(512):
            obs = np.ones(obs_shape) * i
            rb.add(obs=obs,act=act,rew=rew,next_obs=obs+1,done=done)

        sample = rb._encode_sample(range(buffer_size))

        ith = rb.get_next_index()
        np.testing.assert_allclose(np.roll(sample["obs"],-ith-1,axis=0)[1:],
                                   np.roll(sample["next_obs"],-ith-1,axis=0)[:-1])

    def test_stack(self):
        buffer_size = 256
        obs_shape = (4,16,16)
        act_dim = 5

        rb = create_buffer(buffer_size,{"obs": {"shape": obs_shape},
                                        "act": {"shape": act_dim},
                                        "rew": {},
                                        "done": {}},
                           next_of = "obs",
                           stack_compress = "obs")

        obs = np.random.random((buffer_size+obs_shape[0],*(obs_shape[1:])))
        act = np.ones(act_dim)
        rew = 0.5
        done = 0

        for i in range(buffer_size):
            rb.add(obs=obs[i:i+obs_shape[0]],
                   act=act,
                   rew=rew,
                   next_obs=obs[i+1:i+1+obs_shape[0]],
                   done=done)

        np.testing.assert_allclose(rb._encode_sample(range(buffer_size))["obs"],
                                   obs)
        np.testing.assert_allclose(rb._encode_sample(buffer_size-1)["next_obs"],
                                   obs[buffer_size-4:buffer_size])

class TestExperimentalPrioritizedReplayBuffer(unittest.TestCase):
    def test_add(self):
        buffer_size = 500
        obs_shape = (84,84,3)
        act_dim = 10

        rb = PrioritizedReplayBuffer(buffer_size,{"obs": {"shape": obs_shape},
                                                  "act": {"shape": act_dim},
                                                  "rew": {},
                                                  "done": {}},
                                     next_of = ("obs"))

        obs = np.zeros(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done)

        ps = 1.5

        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done,priorities=ps)

        self.assertAlmostEqual(rb.get_max_priority(),1.5)

        obs = np.stack((obs,obs))
        act = np.stack((act,act))
        rew = (1,0)
        done = (0.0,1.0)

        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done)

        ps = (0.2,0.4)
        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done,priorities=ps)


        rb.clear()
        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

    def test_sample(self):
        buffer_size = 500
        obs_shape = (84,84,3)
        act_dim = 4

        rb = PrioritizedReplayBuffer(buffer_size,{"obs": {"shape": obs_shape},
                                                  "act": {"shape": act_dim},
                                                  "rew": {},
                                                  "done": {}},
                                     next_of = "obs")

        obs = np.zeros(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done)

        ps = 1.5

        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done,priorities=ps)

        self.assertAlmostEqual(rb.get_max_priority(),1.5)

        obs = np.stack((obs,obs))
        act = np.stack((act,act))
        rew = (1,0)
        done = (0.0,1.0)

        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done)

        ps = (0.2,0.4)
        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done,priorities=ps)

        sample = rb.sample(64)

        w = sample["weights"]
        i = sample["indexes"]

        rb.update_priorities(i,w*w)

class TestCreateBuffer(unittest.TestCase):
    def test_create(self):
        buffer_size = 256
        obs_shape = (4,84,84)
        act_dim = 3

        rb = create_buffer(buffer_size,
                           env_dict={"obs": {"shape": obs_shape},
                                     "act": {"shape": act_dim},
                                     "rew": {},
                                     "done": {}},
                           next_of = "obs")
        per = create_buffer(buffer_size,
                            env_dict={"obs": {"shape": obs_shape},
                                      "act": {"shape": act_dim},
                                      "rew": {},
                                      "done": {}},
                            next_of = "obs",
                            prioritized = True)

        self.assertIs(type(rb),ReplayBuffer)
        self.assertIs(type(per),PrioritizedReplayBuffer)

        obs = np.random.random(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done)
        per.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done)

        o = rb.sample(1)["obs"]
        po = per.sample(1)["obs"]

        np.testing.assert_allclose(o,obs.reshape((-1,*obs.shape)))
        np.testing.assert_allclose(po,obs.reshape((-1,*obs.shape)))

        rb.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done)
        per.add(obs=obs,act=act,rew=rew,next_obs=obs,done=done)

        no = rb._encode_sample((0))["next_obs"]
        pno = per._encode_sample((0))["next_obs"]

        np.testing.assert_allclose(no,obs.reshape((-1,*obs.shape)))
        np.testing.assert_allclose(pno,obs.reshape((-1,*obs.shape)))

class TestIssue(unittest.TestCase):
    def test_issue51(self):
        buffer_size = 256
        obs_shape = 15
        act_dim = 3

        rb = create_buffer(buffer_size,
                           env_dict={"obs": {"shape": obs_shape},
                                     "act": {"shape": act_dim},
                                     "rew": {},
                                     "done": {}},
                           next_of = "obs")

        obs = np.arange(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        next_obs = obs + 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,next_obs=next_obs,done=done)

        np.testing.assert_allclose(rb._encode_sample((0))["next_obs"][0],
                                   next_obs)

if __name__ == '__main__':
    unittest.main()
